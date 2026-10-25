"""Speed guards: query budgets (every query is a network round trip to a hosted database), the cache,
compression, static-file caching headers and index creation."""
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.cache import clear_caches
from app.config import settings
from app.database import INDEXES, Base, ensure_indexes, get_db
from app.main import STATIC_DIR, app
from app.models import Article, MetricSnapshot, TechScore
from app.collectors.base import get_or_create_source
from app.normalize import resolve_technology
from app.seed import CATALOG, seed

counter = {"n": 0}


@pytest.fixture()
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(session)
    src = get_or_create_source(session, "t")
    for slug, score in {"python": 90, "react": 80, "fastapi": 60, "django": 55, "typescript": 70}.items():
        tid = resolve_technology(session, slug).id
        session.add(TechScore(technology_id=tid, computed_on=date.today(), devintel_score=score, growth_30d=0.1, is_emerging=False))
        session.add(MetricSnapshot(technology_id=tid, source_id=src.id, metric="github.repo_count", value=1000, captured_on=date.today()))
    session.add(Article(source="devto", external_id="1", title="Post", url="https://dev.to/1", tags=["python", "fastapi"], score=5, comments=0,
                        published_at=datetime.now(timezone.utc), fetched_on=date.today(), technology_id=resolve_technology(session, "fastapi").id))
    session.commit()

    @event.listens_for(engine, "before_cursor_execute")
    def _count(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    app.dependency_overrides[get_db] = lambda: session
    clear_caches()
    yield TestClient(app), engine, session
    app.dependency_overrides.clear()
    clear_caches()


def queries(client, method, path, **kw):
    counter["n"] = 0
    r = getattr(client, method)(path, **kw)
    assert r.status_code == 200, (path, r.status_code, r.text)
    return counter["n"]


def test_query_budgets(env):
    client, _, _ = env
    budgets = [("get", "/rankings/trending?limit=100", 1), ("get", "/rankings/emerging", 1), ("get", "/categories", 1),
               ("get", "/pipeline/runs", 1), ("get", "/rankings/breakdown", 2), ("get", "/feed/news", 1), ("get", "/feed/repos", 1), ("get", "/feed/blogs", 1),
               ("get", "/technologies/python", 4), ("get", "/topics", 1), ("get", "/technologies/python/page", 10), ("get", "/compare?techs=fastapi,django", 5),
               ("get", "/discussions?kind=technology&ref=python", 2)]
    for method, path, budget in budgets:
        used = queries(client, method, path)
        assert used <= budget, f"{path} used {used} queries, budget is {budget}"
    used = queries(client, "post", "/skills/gap", json={"skills": ["python", "react"]})
    assert used <= 10, f"/skills/gap used {used} queries (it used 17 before the speed work)"


def test_cache_serves_repeat_requests_without_the_database(env, monkeypatch):
    client, _, session = env
    monkeypatch.setattr(settings, "cache_seconds", 60)
    first = queries(client, "get", "/rankings/trending")
    assert first >= 1 and queries(client, "get", "/rankings/trending") == 0       # repeat is free
    assert queries(client, "get", "/rankings/trending?limit=1") >= 1               # different parameters are a different answer
    session.query(TechScore).update({"devintel_score": 1})
    session.commit()
    assert client.get("/rankings/trending").json()[0]["devintel_score"] == 90      # still the cached answer
    clear_caches()
    assert client.get("/rankings/trending").json()[0]["devintel_score"] == 1       # fresh after the cache is cleared


def test_cache_off_means_always_fresh(env):
    client, _, session = env                                                       # conftest sets cache_seconds = 0
    assert settings.cache_seconds == 0
    assert queries(client, "get", "/categories") == 1 and queries(client, "get", "/categories") == 1


def test_errors_are_never_cached(env, monkeypatch):
    client, _, _ = env
    monkeypatch.setattr(settings, "cache_seconds", 60)
    assert client.get("/technologies/nope").status_code == 404
    assert client.get("/technologies/nope").status_code == 404


def test_responses_are_compressed(env):
    client, _, _ = env
    r = client.get("/technologies?limit=200", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip" and len(r.json()) == len(CATALOG)


def test_ensure_indexes_is_idempotent(env):
    _, engine, _ = env
    ensure_indexes(engine)
    ensure_indexes(engine)
    names = {i["name"] for t in ("tech_scores", "metric_snapshots") for i in inspect(engine).get_indexes(t)}
    assert {"ix_tech_scores_computed_on", "ix_metric_snapshots_captured_on"} <= names
    assert len(INDEXES) == 2


@pytest.mark.skipif(not (STATIC_DIR / "index.html").exists(), reason="frontend not built (npm run build)")
def test_static_files_cache_headers(env):
    client, _, _ = env
    assert client.get("/").headers["cache-control"] == "no-cache"                   # the page is always rechecked
    asset = next(p for p in (STATIC_DIR / "assets").iterdir() if p.suffix == ".js")
    assert "immutable" in client.get(f"/assets/{asset.name}").headers["cache-control"]   # hashed files are kept for a year


def test_signed_in_startup_is_one_request_with_few_queries(env):
    from starlette.requests import Request
    from app.profile_data import build_profile
    from app.routers.auth import current_user, upsert_google_user
    from app.models import UserBan, WatchlistItem
    client, engine, session = env
    user = upsert_google_user(session, {"sub": "g1", "email": "a@example.com", "name": "Ana"})
    session.add(WatchlistItem(user_id=user.id, technology_id=resolve_technology(session, "python").id))
    session.commit()

    counter["n"] = 0
    profile = build_profile(session, user)
    assert counter["n"] <= 2, f"profile used {counter['n']} queries"          # skills + watchlist (with scores) only
    assert [w.slug for w in profile.watchlist] == ["python"] and profile.watchlist[0].devintel_score == 90

    # the signed-in user and their ban status come from ONE query
    request = Request({"type": "http", "headers": [], "session": {"user_id": user.id}})
    counter["n"] = 0
    assert current_user(request, session).id == user.id and counter["n"] == 1 and request.state.banned is False
    session.add(UserBan(user_id=user.id, reason="x")); session.commit()
    request = Request({"type": "http", "headers": [], "session": {"user_id": user.id}})
    current_user(request, session)
    assert request.state.banned is True

    app.dependency_overrides[current_user] = lambda: user
    body = client.get("/auth/me").json()
    app.dependency_overrides.pop(current_user)
    assert body["authenticated"] and body["banned"] is True and body["profile"]["skills"] == []
    assert [w["slug"] for w in body["profile"]["watchlist"]] == ["python"]
    assert client.get("/auth/me").json()["profile"] is None                      # anonymous: no profile, no database work
