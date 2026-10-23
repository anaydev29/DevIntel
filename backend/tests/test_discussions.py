from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Article, Comment, CommentReport, CommentVote, TrendingRepo
from app.routers.auth import current_user, upsert_google_user
from app.seed import seed


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(s)
    s.add(Article(source="devto", external_id="1", title="Post", url="https://dev.to/1", tags=[], score=5, comments=0,
                  published_at=datetime.now(timezone.utc), fetched_on=date.today()))
    s.add(TrendingRepo(captured_on=date.today(), rank=1, github_id=1, full_name="octo/kit", stars=10, forks=1))
    s.commit()
    yield s
    s.close()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def user(db, n, name):
    u = upsert_google_user(db, {"sub": f"g{n}", "email": f"u{n}@example.com", "name": name})
    u.created_at = datetime.now(timezone.utc) - timedelta(days=2)      # older than a day, so their reports count
    db.commit()
    return u


def act_as(u):
    app.dependency_overrides[current_user] = (lambda: u) if u else (lambda: None)


def post(client, body, kind="technology", ref="python", parent=None):
    return client.post("/discussions/comments", json={"kind": kind, "ref": ref, "body": body, "parent_id": parent})


def test_anonymous_can_read_but_not_write(client, db):
    act_as(None)
    assert client.get("/discussions", params={"kind": "technology", "ref": "python"}).json()["total"] == 0
    assert post(client, "hi").status_code == 401


def test_post_alias_names_and_privacy(client, db):
    act_as(user(db, 1, "Anay Kumar Shivhare"))
    r = post(client, "Is React worth it?", ref="reactjs")
    assert r.status_code == 201
    d = r.json()
    assert d["ref"] == "react" and d["total"] == 1
    assert d["comments"][0]["author"] == {"name": "Anay S.", "initial": "A"}      # never the full name or email
    assert "@" not in str(d)
    assert client.get("/discussions/counts", params={"kind": "technology", "refs": "react,python"}).json() == {"react": 1}


def test_replies_stay_one_level_deep(client, db):
    act_as(user(db, 1, "Ana"))
    top = post(client, "top").json()["comments"][0]["id"]
    d = post(client, "reply", parent=top).json()
    reply_id = d["comments"][0]["replies"][0]["id"]
    d = post(client, "reply to the reply", parent=reply_id).json()
    assert len(d["comments"]) == 1 and [r["body"] for r in d["comments"][0]["replies"]] == ["reply", "reply to the reply"]
    assert d["total"] == 3


def test_validation_rules(client, db):
    act_as(user(db, 1, "Ana"))
    assert post(client, "   ").status_code == 422
    assert post(client, "x" * 2001).status_code == 422
    assert post(client, "see http://a.com http://b.com https://c.com").status_code == 422     # too many links
    assert post(client, "ok", kind="forum").status_code == 422
    assert post(client, "ok", ref="nope").status_code == 404
    assert post(client, "ok", kind="article", ref="999").status_code == 404
    assert post(client, "nice article", kind="article", ref="1").status_code == 201
    assert post(client, "nice repo", kind="repo", ref="octo/kit").status_code == 201
    assert post(client, "same text").status_code == 201
    assert post(client, "same text").status_code == 422                                      # duplicate


def test_rate_limit(client, db):
    act_as(user(db, 1, "Ana"))
    for i in range(10):
        assert post(client, f"comment {i}").status_code == 201
    assert post(client, "one too many").status_code == 429


def test_edit_and_delete_only_by_author(client, db):
    a, b = user(db, 1, "Ana"), user(db, 2, "Bo")
    act_as(a)
    cid = post(client, "original").json()["comments"][0]["id"]
    reply_id = None
    act_as(b)
    assert client.put(f"/discussions/comments/{cid}", json={"body": "hacked"}).status_code == 403
    assert client.delete(f"/discussions/comments/{cid}").status_code == 403
    d = post(client, "reply from Bo", parent=cid).json()
    act_as(a)
    d = client.put(f"/discussions/comments/{cid}", json={"body": "edited"}).json()
    assert d["comments"][0]["body"] == "edited" and d["comments"][0]["edited_at"] is not None
    d = client.delete(f"/discussions/comments/{cid}").json()
    assert d["comments"][0]["body"] == "[deleted]" and d["comments"][0]["author"] is None     # kept as a placeholder: it has a reply
    assert d["comments"][0]["replies"][0]["body"] == "reply from Bo"
    assert d["total"] == 1


def test_deleted_comment_without_replies_disappears(client, db):
    act_as(user(db, 1, "Ana"))
    cid = post(client, "bye").json()["comments"][0]["id"]
    assert client.delete(f"/discussions/comments/{cid}").json()["comments"] == []


def test_votes(client, db):
    a, b = user(db, 1, "Ana"), user(db, 2, "Bo")
    act_as(a)
    cid = post(client, "good point").json()["comments"][0]["id"]
    assert client.put(f"/discussions/comments/{cid}/vote", json={"voted": True}).status_code == 422   # own comment
    act_as(b)
    assert client.put(f"/discussions/comments/{cid}/vote", json={"voted": True}).json() == {"score": 1, "voted": True}
    assert client.put(f"/discussions/comments/{cid}/vote", json={"voted": True}).json()["score"] == 1  # idempotent
    seen = client.get("/discussions", params={"kind": "technology", "ref": "python"}).json()["comments"][0]
    assert seen["score"] == 1 and seen["voted"] is True and seen["mine"] is False
    assert client.put(f"/discussions/comments/{cid}/vote", json={"voted": False}).json() == {"score": 0, "voted": False}


def test_three_reports_hide_a_comment(client, db):
    author = user(db, 1, "Ana")
    act_as(author)
    cid = post(client, "spammy text").json()["comments"][0]["id"]
    assert client.post(f"/discussions/comments/{cid}/report", json={"reason": "spam"}).status_code == 422   # own
    for n in (2, 3, 4):
        act_as(user(db, n, f"Reporter{n}"))
        assert client.post(f"/discussions/comments/{cid}/report", json={"reason": "spam"}).status_code == 204
        client.post(f"/discussions/comments/{cid}/report", json={"reason": "spam"})                        # repeat counts once
        shown = client.get("/discussions", params={"kind": "technology", "ref": "python"}).json()["comments"]
        assert bool(shown) == (n < 4)                                                                       # gone after the 3rd reporter
    assert db.query(CommentReport).count() == 3


def test_account_deletion_removes_discussion_data(client, db):
    a, b = user(db, 1, "Ana"), user(db, 2, "Bo")
    act_as(a)
    cid = post(client, "mine").json()["comments"][0]["id"]
    act_as(b)
    post(client, "reply on mine", parent=cid)
    client.put(f"/discussions/comments/{cid}/vote", json={"voted": True})
    act_as(a)
    assert client.delete("/me").status_code == 204
    assert db.query(Comment).count() == 0 and db.query(CommentVote).count() == 0
