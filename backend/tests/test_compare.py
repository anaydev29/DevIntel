from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.analysis import compute_scores
from app.collectors.base import get_or_create_source
from app.database import Base, get_db
from app.main import app
from app.models import MetricSnapshot
from app.normalize import resolve_technology
from app.seed import seed

METRICS = ["github.repo_count", "stackoverflow.questions_30d", "hackernews.stories_30d"]
DATA = {"python": [1_000_000, 20_000, 300], "react": [500_000, 8_000, 120], "rust": [200_000, 3_000, 150]}


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(db)
    src = get_or_create_source(db, "t")
    for slug, values in DATA.items():
        for metric, value in zip(METRICS, values):
            db.add(MetricSnapshot(technology_id=resolve_technology(db, slug).id, source_id=src.id,
                                  metric=metric, value=value, captured_on=date.today()))
    db.commit()
    compute_scores(db)
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()
    db.close()


def test_compare_two_with_alias(client):
    body = client.get("/compare", params={"techs": "python,reactjs"}).json()
    py, react = body["technologies"]
    assert (py["slug"], react["slug"]) == ("python", "react")          # order preserved, alias resolved
    assert py["devintel_score"] > react["devintel_score"]
    assert py["metrics"]["stackoverflow.questions_30d"] == 20_000
    assert len(py["history"]) == 1 and py["history"][0]["date"] == date.today().isoformat()


def test_compare_validation(client):
    assert client.get("/compare", params={"techs": "python"}).status_code == 422
    assert client.get("/compare", params={"techs": "python,py"}).status_code == 422       # same technology twice
    assert client.get("/compare", params={"techs": "python,nope"}).status_code == 404
    assert client.get("/compare", params={"techs": "python,react,rust,go"}).status_code == 422
    assert len(client.get("/compare", params={"techs": "python,react,rust"}).json()["technologies"]) == 3
