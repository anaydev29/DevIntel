from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.collectors.base import get_or_create_source, save_metric
from app.database import Base, get_db
from app.main import STATIC_DIR, app
from app.models import MetricSnapshot, Technology
from app.normalize import resolve_technology
from app.seed import seed


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


def test_alias_resolution(db):
    assert resolve_technology(db, "ReactJS").slug == "react"
    assert resolve_technology(db, "golang").slug == "go"
    assert resolve_technology(db, "k8s").slug == "kubernetes"
    assert resolve_technology(db, "nonexistent") is None


def test_seed_is_idempotent(db):
    before = db.query(Technology).count()
    assert seed(db) == 0
    assert db.query(Technology).count() == before


def test_save_metric_upserts(db):
    tech = resolve_technology(db, "python")
    src = get_or_create_source(db, "github")
    save_metric(db, tech.id, src.id, "github.repo_count", 100)
    save_metric(db, tech.id, src.id, "github.repo_count", 150)
    db.commit()
    rows = db.query(MetricSnapshot).all()
    assert len(rows) == 1 and rows[0].value == 150


def test_list_and_filter(client):
    assert client.get("/health").json() == {"status": "ok"}
    langs = client.get("/technologies", params={"category": "language"}).json()
    assert langs and all(t["category"] == "language" for t in langs)
    assert [t["slug"] for t in client.get("/technologies", params={"q": "fast"}).json()] == ["fastapi"]
    assert "database" in client.get("/categories").json()


def test_detail_by_alias_and_metrics(client, db):
    tech = resolve_technology(db, "react")
    src = get_or_create_source(db, "github")
    save_metric(db, tech.id, src.id, "github.top_stars", 500000)
    db.commit()
    detail = client.get("/technologies/reactjs").json()
    assert detail["slug"] == "react"
    assert detail["latest_metrics"]["github.top_stars"] == 500000
    pts = client.get("/technologies/react/metrics", params={"metric": "github.top_stars"}).json()
    assert pts[0]["captured_on"] == date.today().isoformat()
    assert client.get("/technologies/nope").status_code == 404


@pytest.mark.skipif(not (STATIC_DIR / "index.html").exists(), reason="frontend not built (npm run build)")
def test_frontend_is_served_and_api_still_wins(client):
    page = client.get("/")
    assert page.status_code == 200 and "root" in page.text
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/technologies/nope").status_code == 404
