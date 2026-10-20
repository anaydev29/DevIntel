from datetime import date, datetime, timedelta, timezone

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.github_profile import detect_technologies
from app.main import app
from app.models import Article, TechScore
from app.normalize import resolve_technology
from app.routers.skills import github_client
from app.seed import seed

NOW = datetime.now(timezone.utc)
# slug: (score, growth, emerging)
SCORES = {"python": (90, 0.02, False), "react": (80, 0.01, False), "typescript": (70, 0.05, False),
          "fastapi": (60, 0.40, True), "django": (55, 0.0, False), "rust": (40, None, False), "deno": (30, None, False)}
# dev.to articles: which technology tags appear together
ARTICLES = [["python", "fastapi"]] * 6 + [["python", "django"]] * 2 + [["react", "typescript"]] * 5


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(session)
    for slug, (score, growth, emerging) in SCORES.items():
        session.add(TechScore(technology_id=resolve_technology(session, slug).id, computed_on=date.today(),
                              devintel_score=score, growth_30d=growth, is_emerging=emerging))
    fastapi_id = resolve_technology(session, "fastapi").id
    for i, tags in enumerate(ARTICLES):
        session.add(Article(source="devto", external_id=str(i), title=f"Post {i}", url=f"https://dev.to/{i}", tags=tags,
                            published_at=NOW - timedelta(days=2), score=10 + i, comments=0, fetched_on=date.today(),
                            technology_id=fastapi_id if "fastapi" in tags else None))
    session.commit()
    yield session
    session.close()


def fake_github(handler):
    return lambda: httpx.Client(transport=httpx.MockTransport(handler))


def repos_ok(request):
    return httpx.Response(200, json=[
        {"fork": False, "language": "Python", "topics": ["fastapi", "docker"]},
        {"fork": False, "language": "Python", "topics": []},
        {"fork": True, "language": "Rust", "topics": []},            # forks are ignored
        {"fork": False, "language": "HTML", "topics": ["portfolio"]},  # not a tracked technology
    ])


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[github_client] = fake_github(repos_ok)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_manual_skills_recommend_related_first(client):
    body = client.post("/skills/gap", json={"skills": ["Python", "bogus-tech"]}).json()
    assert [k["slug"] for k in body["known"]] == ["python"] and body["unrecognized"] == ["bogus-tech"]
    slugs = [r["slug"] for r in body["recommendations"]]
    assert "python" not in slugs                                   # never recommend what they already know
    assert slugs[0] == "fastapi"                                   # strong fit + growing + decent score
    top = body["recommendations"][0]
    assert top["related_to"] == ["Python"] and any("Often used with Python" in r for r in top["reasons"])
    assert "Flagged as taking off" in top["reasons"]
    assert body["coverage"]["known_in_top10"] == 1
    assert len(top["starters"]) == 2 and top["starters"][0]["title"] == "Post 5"   # most reacted first


def test_category_filter(client):
    recs = client.post("/skills/gap", json={"skills": ["python"], "category": "framework"}).json()["recommendations"]
    assert recs and all(r["category"] == "framework" for r in recs)


def test_github_detection_and_merge(client):
    body = client.post("/skills/gap", json={"skills": ["react"], "github_username": "@someone"}).json()
    known = {k["slug"]: k for k in body["known"]}
    assert set(known) == {"react", "python", "fastapi", "docker"}   # Rust fork and HTML ignored
    assert known["python"]["source"] == "github" and known["python"]["repos"] == 2
    assert known["react"]["source"] == "manual"
    assert body["github"] == {"username": "someone", "repos_scanned": 3}


def test_validation_and_github_errors(client):
    assert client.post("/skills/gap", json={}).status_code == 422
    assert client.post("/skills/gap", json={"github_username": "bad name!"}).status_code == 422
    app.dependency_overrides[github_client] = fake_github(lambda r: httpx.Response(404))
    assert client.post("/skills/gap", json={"github_username": "ghost"}).status_code == 404
    app.dependency_overrides[github_client] = fake_github(lambda r: httpx.Response(403, headers={"x-ratelimit-remaining": "0"}))
    assert client.post("/skills/gap", json={"github_username": "busy"}).status_code == 503


def test_detect_technologies_counts_each_repo_once(db):
    counts = detect_technologies(db, [{"language": "Python", "topics": ["python", "fastapi"]}])
    assert counts[resolve_technology(db, "python").id] == 1       # language + topic in the same repo = one repo
