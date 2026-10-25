from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cache import clear_caches
from app.database import Base, get_db
from app.main import app
from app.models import Article, Comment, Repository, TechScore, Thread, TopicMeta, UserBan
from app.normalize import resolve_technology
from app.routers.auth import current_user, upsert_google_user
from app.seed import seed

NOW = datetime.now(timezone.utc)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(s)
    s.add(Article(source="devto", external_id="1", title="Blog post", url="https://dev.to/1", tags=["python"], score=5, comments=0,
                  published_at=NOW, fetched_on=date.today()))
    s.commit()
    yield s
    s.close()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    clear_caches()
    yield TestClient(app)
    app.dependency_overrides.clear()


def user(db, n, name="Ana Kumar"):
    u = upsert_google_user(db, {"sub": f"g{n}", "email": f"u{n}@example.com", "name": name})
    u.created_at = NOW - timedelta(days=2)
    db.commit()
    return u


def act_as(u):
    app.dependency_overrides[current_user] = (lambda: u) if u else (lambda: None)


def start(client, title="Is Rust worth learning in 2026?", body="I know Python. Should I learn Rust next?", **extra):
    return client.post("/topics", json={"title": title, "body": body, **extra})


def test_start_a_topic_and_see_it_listed(client, db):
    act_as(user(db, 1))
    article_id = db.query(Article).first().id
    r = start(client, title="  Is   Rust worth learning?  ", technology="rust-lang", article_id=article_id)
    assert r.status_code == 201, r.text
    t = r.json()
    assert t["title"] == "Is Rust worth learning?"                                  # extra spaces collapsed
    assert t["author"] == {"name": "Ana K.", "initial": "A"} and t["technology"] == {"slug": "rust", "name": "Rust"}
    assert t["article"]["id"] == article_id and t["replies"] == 0 and t["preview"].startswith("I know Python")
    listed = client.get("/topics").json()
    assert [x["ref"] for x in listed] == [t["ref"]]
    assert client.get(f"/topics/{t['ref']}").json()["title"] == "Is Rust worth learning?"
    assert [x["ref"] for x in client.get("/topics", params={"tech": "rust"}).json()] == [t["ref"]]
    assert client.get("/topics", params={"tech": "python"}).json() == []
    assert client.get("/topics/nope").status_code == 404


def test_replies_use_the_discussion_engine(client, db):
    act_as(user(db, 1))
    ref = start(client).json()["ref"]
    act_as(user(db, 2, "Bo Rao"))
    d = client.post("/discussions/comments", json={"kind": "general", "ref": ref, "body": "Yes, start with the book."}).json()
    assert d["total"] == 2 and [c["author"]["name"] for c in d["comments"]] == ["Ana K.", "Bo R."]    # opening post comes first
    topic = client.get(f"/topics/{ref}").json()
    assert topic["replies"] == 1
    assert client.get("/discussions/counts", params={"kind": "general", "refs": ref}).json() == {ref: 2}
    assert client.post("/discussions/comments", json={"kind": "general", "ref": "unknown", "body": "hi"}).status_code == 404


def test_activity_sorting(client, db):
    a = user(db, 1)
    act_as(a)
    first = start(client, title="First topic here").json()["ref"]
    second = start(client, title="Second topic here").json()["ref"]
    assert [x["ref"] for x in client.get("/topics", params={"sort": "new"}).json()][0] == second
    client.post("/discussions/comments", json={"kind": "general", "ref": first, "body": "a new reply"})
    assert [x["ref"] for x in client.get("/topics", params={"sort": "active"}).json()][0] == first    # reply moves it up


def test_validation_and_limits(client, db):
    act_as(None)
    assert start(client).status_code == 401
    me = user(db, 1)
    act_as(me)
    assert start(client, title="hey").status_code == 422                                     # too short
    assert start(client, title="x" * 121).status_code == 422
    assert start(client, title="Look at https://spam.example now").status_code == 422        # links stay out of titles
    assert start(client, body="  ").status_code == 422
    assert start(client, body="see http://a.com http://b.com http://c.com").status_code == 422
    assert start(client, technology="nope").status_code == 404
    assert start(client, article_id=9999).status_code == 404
    assert start(client, title="A perfectly fine title").status_code == 201
    assert start(client, title="A perfectly fine title").status_code == 422                  # same title again
    for i in range(4):
        assert start(client, title=f"Another topic number {i}").status_code == 201
    assert start(client, title="One topic too many").status_code == 429                      # 5 per day
    db.add(UserBan(user_id=me.id)); db.commit()
    assert start(client, title="Banned person topic").status_code == 403


def test_removing_the_opening_post_takes_the_topic_down(client, db):
    me = user(db, 1)
    act_as(me)
    t = start(client).json()
    assert client.delete(f"/discussions/comments/{t['first_comment_id']}").status_code == 200
    assert client.get("/topics").json() == [] and client.get(f"/topics/{t['ref']}").status_code == 404


def test_account_deletion_removes_topics_and_replies(client, db):
    a, b = user(db, 1), user(db, 2, "Bo")
    act_as(a); ref = start(client).json()["ref"]
    act_as(b); client.post("/discussions/comments", json={"kind": "general", "ref": ref, "body": "a reply"})
    act_as(a); assert client.delete("/me").status_code == 204
    assert db.query(TopicMeta).count() == 0 and db.query(Thread).filter_by(kind="general").count() == 0
    assert db.query(Comment).count() == 0


def test_technology_page(client, db):
    py = resolve_technology(db, "python")
    fast = resolve_technology(db, "fastapi")
    db.add(TechScore(technology_id=py.id, computed_on=date.today(), devintel_score=90, growth_30d=0.1, is_emerging=False))
    for i, (tags, score) in enumerate([(["python", "fastapi"], 50), (["python", "beginners"], 5), (["python"], 80), (["python", "fastapi"], 20)]):
        db.add(Article(source="devto", external_id=f"p{i}", title=f"Post {i}", url=f"https://dev.to/p{i}", tags=tags, score=score, comments=0,
                       published_at=NOW, fetched_on=date.today(), technology_id=py.id))
    db.add_all([Repository(github_id=1, full_name="a/small", technology_id=py.id, stars=10, forks=1, last_seen=date.today(), language="Python"),
                Repository(github_id=2, full_name="b/big", technology_id=py.id, stars=999, forks=1, last_seen=date.today(), language="Python")])
    db.commit()
    page = client.get("/technologies/py/page").json()                                        # alias works
    assert page["technology"]["slug"] == "python" and page["technology"]["devintel_score"] == 90
    assert [r["slug"] for r in page["related"]] == ["fastapi"] and page["related"][0]["together"] == 2
    assert page["articles"][0]["beginner"] is True and page["articles"][0]["title"] == "Post 1"   # beginner-friendly first
    assert [a["score"] for a in page["articles"][1:]][:2] == sorted([a["score"] for a in page["articles"][1:]], reverse=True)[:2]
    assert [r["full_name"] for r in page["repos"]] == ["b/big", "a/small"] and page["repos"][0]["url"] == "https://github.com/b/big"
    assert client.get("/technologies/nope/page").status_code == 404
