from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import ModerationAction, UserBan
from app.routers.auth import current_user, upsert_google_user
from app.seed import seed


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(s)
    yield s
    s.close()


@pytest.fixture()
def client(db, monkeypatch):
    monkeypatch.setattr(settings, "admin_emails", "boss@example.com")
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def make(db, n, name, email=None, age_days=2):
    u = upsert_google_user(db, {"sub": f"g{n}", "email": email or f"u{n}@example.com", "name": name})
    u.created_at = datetime.now(timezone.utc) - timedelta(days=age_days)
    db.commit()
    return u


def act_as(u):
    app.dependency_overrides[current_user] = (lambda: u) if u else (lambda: None)


def comment(client, text="a comment"):
    return client.post("/discussions/comments", json={"kind": "technology", "ref": "python", "body": text}).json()["comments"][-1]["id"]


def report(client, cid, reason="Spam"):
    return client.post(f"/discussions/comments/{cid}/report", json={"reason": reason})


def test_admin_comes_only_from_server_settings(client, db):
    assert make(db, 1, "Boss", email="Boss@Example.com").role == "admin"        # listed (case-insensitive)
    assert make(db, 2, "Regular").role == "user"
    monkeypatch_list = settings.admin_emails
    settings.admin_emails = ""                                                  # removed from the list -> demoted at next login
    assert upsert_google_user(db, {"sub": "g1", "email": "boss@example.com", "name": "Boss"}).role == "user"
    settings.admin_emails = monkeypatch_list


def test_only_moderators_can_use_moderation(client, db):
    act_as(None)
    assert client.get("/moderation/queue").status_code == 401
    act_as(make(db, 1, "Regular"))
    for path in ("/moderation/queue", "/moderation/log", "/moderation/users"):
        assert client.get(path).status_code == 403, path
    assert client.post("/moderation/comments/1/action", json={"action": "remove"}).status_code == 403


def test_queue_restore_remove_and_log(client, db):
    author, mod = make(db, 1, "Ana Author"), make(db, 2, "Mo Mod")
    mod.role = "moderator"; db.commit()
    reporters = [make(db, n, f"R{n}") for n in (3, 4)]
    act_as(author)
    keep, bad = comment(client, "fine comment"), comment(client, "buy cheap stuff")
    for r, cid, why in [(reporters[0], keep, "Off topic"), (reporters[0], bad, "Spam"), (reporters[1], bad, "Spam")]:
        act_as(r); assert report(client, cid, why).status_code == 204
    act_as(mod)
    cases = client.get("/moderation/queue").json()
    assert [c["comment_id"] for c in cases] == [bad, keep]                      # most reported first
    assert cases[0]["author_name"] == "Ana A." and [r["reason"] for r in cases[0]["reports"]] == ["Spam", "Spam"]
    assert "email" not in str(cases)                                            # moderators never see emails here
    assert client.post(f"/moderation/comments/{keep}/action", json={"action": "restore"}).status_code == 204
    assert client.post(f"/moderation/comments/{bad}/action", json={"action": "remove", "note": "spam ad"}).status_code == 204
    assert client.get("/moderation/queue").json() == []                         # both cases closed
    shown = client.get("/discussions", params={"kind": "technology", "ref": "python"}).json()["comments"]
    assert [c["body"] for c in shown] == ["fine comment"]                       # removed comment disappears (no replies)
    log = client.get("/moderation/log").json()
    assert [(e["action"], e["moderator"]) for e in log] == [("remove", "Mo M."), ("restore", "Mo M.")] and log[0]["note"] == "spam ad"
    assert client.post(f"/moderation/comments/{bad}/action", json={"action": "explode"}).status_code == 422


def test_new_accounts_reports_do_not_auto_hide_but_reach_moderators(client, db):
    author = make(db, 1, "Ana")
    act_as(author); cid = comment(client)
    for n in (2, 3, 4):
        act_as(make(db, n, f"New{n}", age_days=0)); report(client, cid)
    act_as(author)
    assert client.get("/discussions", params={"kind": "technology", "ref": "python"}).json()["comments"][0]["status"] == "visible"
    mod = make(db, 9, "Mod"); mod.role = "moderator"; db.commit(); act_as(mod)
    assert len(client.get("/moderation/queue").json()) == 1                      # still visible to moderators


def test_restore_after_auto_hide_is_not_instantly_undone(client, db):
    author = make(db, 1, "Ana")
    act_as(author); cid = comment(client)
    for n in (2, 3, 4):
        act_as(make(db, n, f"Old{n}")); report(client, cid)
    mod = make(db, 9, "Mod"); mod.role = "moderator"; db.commit(); act_as(mod)
    assert client.get("/moderation/queue").json()[0]["status"] == "hidden"
    client.post(f"/moderation/comments/{cid}/action", json={"action": "restore"})
    act_as(make(db, 5, "Late")); report(client, cid)                              # one more report after the decision
    act_as(author)
    assert client.get("/discussions", params={"kind": "technology", "ref": "python"}).json()["comments"][0]["status"] == "visible"


def test_ban_blocks_writing_but_not_reading_or_deleting_own(client, db):
    user, mod = make(db, 1, "Troll"), make(db, 2, "Mod")
    mod.role = "moderator"; db.commit()
    act_as(user); cid = comment(client)
    act_as(mod)
    assert client.post(f"/moderation/users/{user.id}/ban", json={"reason": "harassment"}).status_code == 204
    assert client.post(f"/moderation/users/{user.id}/ban", json={"reason": "again"}).status_code == 204     # idempotent
    assert db.query(UserBan).count() == 1
    act_as(user)
    assert client.get("/auth/me").json()["banned"] is True
    body = {"kind": "technology", "ref": "python", "body": "hello"}
    assert client.post("/discussions/comments", json=body).status_code == 403
    assert client.put(f"/discussions/comments/{cid}", json={"body": "edit"}).status_code == 403
    assert client.get("/discussions", params={"kind": "technology", "ref": "python"}).status_code == 200      # can still read
    assert client.delete(f"/discussions/comments/{cid}").status_code == 200                                   # can delete own
    act_as(mod)
    assert client.delete(f"/moderation/users/{user.id}/ban").status_code == 204
    act_as(user)
    assert client.post("/discussions/comments", json=body).status_code == 201                                  # unbanned


def test_ban_permission_rules(client, db):
    boss = make(db, 1, "Boss", email="boss@example.com")                       # admin
    mod_a, mod_b, user = make(db, 2, "ModA"), make(db, 3, "ModB"), make(db, 4, "User")
    mod_a.role = mod_b.role = "moderator"; db.commit()
    act_as(mod_a)
    assert client.post(f"/moderation/users/{mod_a.id}/ban", json={}).status_code == 422       # not yourself
    assert client.post(f"/moderation/users/{boss.id}/ban", json={}).status_code == 403        # never admins
    assert client.post(f"/moderation/users/{mod_b.id}/ban", json={}).status_code == 403       # moderators cannot ban moderators
    assert client.post(f"/moderation/users/{user.id}/ban", json={}).status_code == 204
    act_as(boss)
    assert client.post(f"/moderation/users/{mod_b.id}/ban", json={}).status_code == 204       # admins can


def test_admin_appoints_moderators(client, db):
    boss, user, mod = make(db, 1, "Boss", email="boss@example.com"), make(db, 2, "User"), make(db, 3, "Mod")
    mod.role = "moderator"; db.commit()
    act_as(mod)
    assert client.get("/moderation/users").status_code == 403                                  # admin only
    assert client.put(f"/moderation/users/{user.id}/role", json={"role": "moderator"}).status_code == 403
    act_as(boss)
    listed = client.get("/moderation/users").json()
    assert {u["email"] for u in listed} >= {"u2@example.com", "boss@example.com"}
    assert client.put(f"/moderation/users/{user.id}/role", json={"role": "moderator"}).status_code == 204
    assert client.get("/auth/me").json()["user"]["role"] == "admin"
    act_as(db.get(type(user), user.id))
    assert client.get("/moderation/queue").status_code == 200                                  # the new moderator can now use it
    act_as(boss)
    assert client.put(f"/moderation/users/{user.id}/role", json={"role": "admin"}).status_code == 422
    assert client.put(f"/moderation/users/{boss.id}/role", json={"role": "user"}).status_code == 403
    assert client.put(f"/moderation/users/{user.id}/role", json={"role": "user"}).status_code == 204
    assert [e.action for e in db.query(ModerationAction).order_by(ModerationAction.id)] == ["promote", "demote"]
