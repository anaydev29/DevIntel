from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.collectors.devto import DevToCollector
from app.collectors.hn_frontpage import HackerNewsFrontPageCollector
from app.database import Base, get_db
from app.main import app
from app.models import Article, Comment, CommentReport, Thread
from app.routers.auth import current_user, upsert_google_user
from app.seed import seed

NOW = datetime.now(timezone.utc)


@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(s)
    app.dependency_overrides[get_db] = lambda: s
    yield TestClient(app), engine, s
    app.dependency_overrides.clear()
    s.close()


def person(db, n, name="Ana"):
    u = upsert_google_user(db, {"sub": f"g{n}", "email": f"u{n}@example.com", "name": name})
    u.created_at = NOW - timedelta(days=2); db.commit()
    return u


def act_as(u):
    app.dependency_overrides[current_user] = lambda: u


def test_dangerous_links_are_never_stored(env):
    _, _, db = env
    hn = {"hits": [{"objectID": "1", "title": "Evil", "url": "javascript:alert(document.cookie)", "points": 5, "num_comments": 0, "created_at_i": int(NOW.timestamp())},
                   {"objectID": "2", "title": "Data", "url": "data:text/html,<script>1</script>", "points": 5, "num_comments": 0, "created_at_i": int(NOW.timestamp())},
                   {"objectID": "3", "title": "Fine", "url": "https://example.com/x", "points": 5, "num_comments": 0, "created_at_i": int(NOW.timestamp())}]}
    HackerNewsFrontPageCollector(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=hn)))).run(db)
    urls = {a.external_id: a.url for a in db.query(Article)}
    assert urls["1"] == "https://news.ycombinator.com/item?id=1" and urls["2"] == "https://news.ycombinator.com/item?id=2"   # fall back to the HN page
    assert urls["3"] == "https://example.com/x"

    posts = [{"id": 1, "title": "Bad", "url": "javascript:alert(1)", "tag_list": [], "published_timestamp": NOW.isoformat()},
             {"id": 2, "title": "Good", "url": "https://dev.to/good", "tag_list": [], "published_timestamp": NOW.isoformat()}]
    DevToCollector(client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=posts))), delay=0).run(db, only_slugs=["python"])
    assert {a.title for a in db.query(Article).filter_by(source="devto")} == {"Good"}                                        # the bad one is skipped


def test_double_clicks_never_become_server_errors(env, monkeypatch):
    client, _, db = env
    a, b = person(db, 1), person(db, 2, "Bo")
    act_as(a)
    cid = client.post("/discussions/comments", json={"kind": "technology", "ref": "python", "body": "hi"}).json()["comments"][0]["id"]
    act_as(b)
    real_commit, state = db.commit, {"fail": True}

    def flaky_commit():                       # the database says "that row already exists", as it would for a simultaneous double click
        if state["fail"]:
            state["fail"] = False
            raise IntegrityError("INSERT", {}, Exception("duplicate"))
        return real_commit()
    monkeypatch.setattr(db, "commit", flaky_commit)
    assert client.put(f"/discussions/comments/{cid}/vote", json={"voted": True}).status_code == 200
    state["fail"] = True
    assert client.post(f"/discussions/comments/{cid}/report", json={"reason": "Spam"}).status_code == 204
    assert db.query(CommentReport).count() == 0 or db.query(CommentReport).count() == 1      # no crash either way


def test_moderation_queue_uses_a_fixed_number_of_queries(env):
    client, engine, db = env
    mod = person(db, 99, "Mod"); mod.role = "moderator"; db.commit()
    reporter = person(db, 50, "Reporter")
    t = Thread(kind="technology", ref="python"); db.add(t); db.flush()
    for i in range(8):                                        # 8 different authors, each with a reported comment
        author = person(db, 100 + i, f"Author{i}")
        c = Comment(thread_id=t.id, author_id=author.id, body=f"comment {i}"); db.add(c); db.flush()
        db.add(CommentReport(comment_id=c.id, reporter_id=reporter.id, reason="Spam"))
    db.commit()
    act_as(mod)
    counter = {"n": 0}

    @event.listens_for(engine, "before_cursor_execute")
    def _count(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1
    body = client.get("/moderation/queue").json()
    assert len(body) == 8 and counter["n"] <= 5, f"{counter['n']} queries for 8 cases"
