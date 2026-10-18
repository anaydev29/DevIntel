from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.collectors.devto import DevToCollector
from app.collectors.hn_frontpage import HackerNewsFrontPageCollector
from app.collectors.trending_repos import TrendingReposCollector
from app.database import Base, get_db
from app.main import app
from app.models import Article, TrendingRepo
from app.seed import seed

NOW = datetime.now(timezone.utc)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(session)
    yield session
    session.close()


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def devto_handler(request):
    tag = request.url.params["tag"]
    return httpx.Response(200, json=[
        {"id": 1, "title": f"Intro to {tag}", "url": f"https://dev.to/a/{tag}", "user": {"name": "Ana"},
         "tag_list": [tag, "beginners"], "published_timestamp": NOW.isoformat(),
         "public_reactions_count": 50, "comments_count": 3, "reading_time_minutes": 5},
        {"id": 2, "title": "Old post", "url": "https://dev.to/a/old", "user": {"name": "Bo"},
         "tags": "x, y", "published_at": (NOW - timedelta(days=40)).isoformat(), "public_reactions_count": 999},
    ])


def test_devto_collector_and_blogs_endpoint(db):
    collector = DevToCollector(client=client_for(devto_handler), delay=0)
    run = collector.run(db, only_slugs=["python"])
    assert run.status == "success" and run.records_fetched == 2
    collector.run(db, only_slugs=["python"])                      # re-run must not duplicate
    assert db.query(Article).count() == 2

    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    posts = c.get("/feed/blogs").json()
    assert [p["title"] for p in posts] == ["Intro to python"]     # 40-day-old post is outside the window
    assert posts[0]["technology"] == "python" and posts[0]["score"] == 50
    assert c.get("/feed/blogs", params={"tech": "py"}).json()[0]["title"] == "Intro to python"  # alias works
    assert c.get("/feed/blogs", params={"tech": "nope"}).status_code == 404
    app.dependency_overrides.clear()


def test_hn_frontpage_collector_and_news_endpoint(db):
    def handler(request):
        return httpx.Response(200, json={"hits": [
            {"objectID": "11", "title": "Big launch", "url": "https://example.com/x", "author": "u1",
             "points": 300, "num_comments": 80, "created_at_i": int(NOW.timestamp())},
            {"objectID": "12", "title": "Ask HN: Learn Rust?", "url": None, "author": "u2",
             "points": 90, "num_comments": 40, "created_at_i": int(NOW.timestamp())}]})
    run = HackerNewsFrontPageCollector(client=client_for(handler)).run(db)
    assert run.status == "success" and run.records_fetched == 2

    app.dependency_overrides[get_db] = lambda: db
    items = TestClient(app).get("/feed/news").json()
    assert [i["title"] for i in items] == ["Big launch", "Ask HN: Learn Rust?"]   # sorted by points
    assert items[1]["url"].endswith("item?id=12")                                   # Ask HN links to discussion
    assert items[0]["discussion_url"] == "https://news.ycombinator.com/item?id=11"
    app.dependency_overrides.clear()


def test_trending_repos_collector_dedupes_and_ranks(db):
    def handler(request):
        q = request.url.params["q"]
        items = [{"id": 1, "full_name": "a/big", "description": "Big repo", "language": "Python",
                  "stargazers_count": 5000, "forks_count": 100, "created_at": "2026-10-14T10:00:00Z"}]
        if "language:rust" in q:
            items.append({"id": 2, "full_name": "b/small", "description": None, "language": "Rust",
                          "stargazers_count": 900, "forks_count": 10, "created_at": "2026-10-15T10:00:00Z"})
        return httpx.Response(200, json={"items": items})
    run = TrendingReposCollector(token="x", client=client_for(handler), delay=0).run(db)
    assert run.status == "success" and run.records_fetched == 2     # repo 1 returned by every query, stored once
    assert [r.full_name for r in db.query(TrendingRepo).order_by(TrendingRepo.rank)] == ["a/big", "b/small"]

    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    assert len(c.get("/feed/repos").json()) == 2
    only_rust = c.get("/feed/repos", params={"language": "rust"}).json()
    assert [r["full_name"] for r in only_rust] == ["b/small"] and only_rust[0]["url"] == "https://github.com/b/small"
    app.dependency_overrides.clear()


def test_feed_endpoints_empty_before_first_run(db):
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    assert c.get("/feed/blogs").json() == [] and c.get("/feed/news").json() == [] and c.get("/feed/repos").json() == []
    app.dependency_overrides.clear()
