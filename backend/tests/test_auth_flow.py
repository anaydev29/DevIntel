"""The real sign-in path: signed cookie, current_user and the Google callback, with a stand-in for Google.
(Other tests replace current_user to save work, so these are the only tests that use the real cookie.)"""
import pytest
from authlib.integrations.base_client.errors import OAuthError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.responses import RedirectResponse

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import User, UserBan
from app.routers import auth as auth_module
from app.seed import seed

INFO = {"sub": "google-1", "email": "ana@example.com", "email_verified": True, "name": "Ana Kumar", "picture": None}


class FakeGoogle:
    def __init__(self, info=None, fail=False):
        self.info, self.fail, self.redirect_uri = info, fail, None

    async def authorize_redirect(self, request, redirect_uri):
        self.redirect_uri = redirect_uri
        return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?client_id=x", status_code=302)

    async def authorize_access_token(self, request):
        if self.fail:
            raise OAuthError("access_denied")
        return {"userinfo": self.info}


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(s)
    yield s
    s.close()


@pytest.fixture()
def setup(db, monkeypatch):
    app.dependency_overrides[get_db] = lambda: db
    fake = FakeGoogle(INFO)
    monkeypatch.setattr(auth_module.oauth, "create_client", lambda name: fake)
    client = TestClient(app, follow_redirects=False)
    yield client, fake, db
    app.dependency_overrides.clear()


def sign_in(client, db_=None):
    r = client.get("/auth/google/callback", params={"code": "c", "state": "s"})
    assert r.status_code in (302, 307) and r.headers["location"] == "/", r.headers
    return r


def test_login_redirects_to_google_with_the_right_return_address(setup, monkeypatch):
    client, fake, _ = setup
    r = client.get("/auth/google/login")
    assert r.status_code == 302 and r.headers["location"].startswith("https://accounts.google.com/")
    assert fake.redirect_uri == "http://testserver/auth/google/callback"
    monkeypatch.setattr(settings, "public_base_url", "https://devintel.example.com/")         # behind a proxy / in production
    client.get("/auth/google/login")
    assert fake.redirect_uri == "https://devintel.example.com/auth/google/callback"


def test_login_is_unavailable_without_google_keys(db, monkeypatch):
    app.dependency_overrides[get_db] = lambda: db
    monkeypatch.setattr(auth_module.oauth, "create_client", lambda name: None)
    client = TestClient(app, follow_redirects=False)
    assert client.get("/auth/google/login").status_code == 503 and client.get("/auth/google/callback").status_code == 503
    me = client.get("/auth/me").json()
    assert me["login_enabled"] is False and me["authenticated"] is False
    app.dependency_overrides.clear()


def test_callback_signs_you_in_with_a_secure_cookie_and_me_works(setup):
    client, _, db = setup
    r = sign_in(client)
    cookie = r.headers["set-cookie"].lower()
    assert "session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie        # not readable by page scripts
    me = client.get("/auth/me").json()                                                       # the real cookie path, no overrides
    assert me["authenticated"] is True and me["user"]["email"] == "ana@example.com" and me["profile"]["skills"] == []
    assert db.query(User).count() == 1
    client.get("/auth/google/callback")                                                      # signing in again does not duplicate
    assert db.query(User).count() == 1


def test_failed_logins_leave_you_signed_out(setup):
    client, fake, db = setup
    fake.fail = True
    r = client.get("/auth/google/callback")
    assert r.headers["location"] == "/?login=failed" and client.get("/auth/me").json()["authenticated"] is False
    fake.fail, fake.info = False, {**INFO, "email_verified": False}                          # unverified Google email: refuse
    assert client.get("/auth/google/callback").headers["location"] == "/?login=failed"
    fake.info = {k: v for k, v in INFO.items() if k != "sub"}
    assert client.get("/auth/google/callback").headers["location"] == "/?login=failed"
    assert db.query(User).count() == 0


def test_logout_and_bad_cookies(setup):
    client, _, db = setup
    sign_in(client)
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").json()["authenticated"] is False
    client.cookies.set("session", "this-is-not-a-valid-signed-cookie")
    assert client.get("/auth/me").status_code == 200 and client.get("/auth/me").json()["authenticated"] is False   # never a 500


def test_cookie_for_a_deleted_user_is_not_a_login(setup):
    client, _, db = setup
    sign_in(client)
    db.query(User).delete(); db.commit()
    assert client.get("/auth/me").json()["authenticated"] is False
    assert client.get("/me/profile").status_code == 401


def test_ban_status_comes_through_the_real_cookie_path(setup):
    client, _, db = setup
    sign_in(client)
    uid = db.query(User).one().id
    body = {"kind": "technology", "ref": "python", "body": "hello"}
    assert client.post("/discussions/comments", json=body).status_code == 201
    db.add(UserBan(user_id=uid)); db.commit()
    assert client.get("/auth/me").json()["banned"] is True
    assert client.post("/discussions/comments", json={**body, "body": "another"}).status_code == 403


def test_admin_from_settings_works_with_the_real_cookie(setup, monkeypatch):
    client, _, _ = setup
    monkeypatch.setattr(settings, "admin_emails", "ana@example.com")
    sign_in(client)
    assert client.get("/auth/me").json()["user"]["role"] == "admin"
    assert client.get("/moderation/queue").status_code == 200
