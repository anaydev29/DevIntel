import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import User, UserSkill, WatchlistItem
from app.routers.auth import current_user, upsert_google_user
from app.seed import seed

INFO = {"sub": "google-123", "email": "anay@example.com", "name": "Anay", "picture": "https://example.com/a.png"}


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(session)
    yield session
    session.close()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def sign_in(db, info=INFO):
    user = upsert_google_user(db, info)
    app.dependency_overrides[current_user] = lambda: user
    return user


def test_upsert_matches_on_google_id_not_email(db):
    first = upsert_google_user(db, INFO)
    again = upsert_google_user(db, {**INFO, "email": "new-address@example.com", "name": "Anay S"})
    assert again.id == first.id and db.query(User).count() == 1
    assert again.email == "new-address@example.com" and again.name == "Anay S"      # details refresh on every login
    assert again.role == "user"


def test_anonymous_visitors(client):
    me = client.get("/auth/me").json()
    assert me["authenticated"] is False and me["user"] is None
    assert me["login_enabled"] is False                                   # no Google keys in the test environment
    assert client.get("/auth/google/login").status_code == 503            # clear message instead of a crash
    for method, path in [("get", "/me/profile"), ("put", "/me/skills"), ("put", "/me/watchlist/react"), ("delete", "/me")]:
        assert getattr(client, method)(path).status_code == 401, path


def test_profile_skills_and_github_username(client, db):
    sign_in(db)
    assert client.get("/auth/me").json()["user"]["email"] == "anay@example.com"
    r = client.put("/me/skills", json={"skills": ["Python", "reactjs", "bogus"]}).json()
    assert r["skills"] == ["python", "react"] and r["unrecognized"] == ["bogus"]
    assert client.put("/me/skills", json={"skills": ["rust"]}).json()["skills"] == ["rust"]   # replaces the list
    assert client.put("/me/skills", json={"skills": ["x"] * 41}).status_code == 422
    assert client.put("/me/profile", json={"github_username": "@anaydev29"}).json()["user"]["github_username"] == "anaydev29"
    assert client.put("/me/profile", json={"github_username": "bad name!"}).status_code == 422
    assert client.put("/me/profile", json={"github_username": ""}).json()["user"]["github_username"] is None


def test_watchlist_add_remove_is_idempotent(client, db):
    sign_in(db)
    client.put("/me/watchlist/fastapi")
    items = client.put("/me/watchlist/FastAPI").json()                    # second add changes nothing
    assert [i["slug"] for i in items] == ["fastapi"]
    assert client.put("/me/watchlist/k8s").json()[0]["slug"] == "kubernetes"     # aliases work; newest first
    assert [i["slug"] for i in client.delete("/me/watchlist/fastapi").json()] == ["kubernetes"]
    assert client.put("/me/watchlist/nope").status_code == 404


def test_users_cannot_see_each_others_data(client, db):
    sign_in(db)
    client.put("/me/skills", json={"skills": ["python"]})
    sign_in(db, {"sub": "other", "email": "b@example.com", "name": "B"})
    assert client.get("/me/profile").json()["skills"] == []


def test_delete_account_removes_everything(client, db):
    user = sign_in(db)
    client.put("/me/skills", json={"skills": ["python"]})
    client.put("/me/watchlist/react")
    assert client.delete("/me").status_code == 204
    assert db.query(User).count() == 0 and db.query(UserSkill).count() == 0 and db.query(WatchlistItem).count() == 0
