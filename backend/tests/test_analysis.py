from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.analysis import compute_scores, growth_rate, percentile_ranks
from app.collectors.base import get_or_create_source
from app.database import Base, get_db
from app.main import app
from app.models import MetricSnapshot, TechScore
from app.normalize import resolve_technology
from app.seed import seed

TODAY = date(2026, 10, 17)
PAST = TODAY - timedelta(days=10)
METRICS = ["github.repo_count", "github.top_stars", "stackoverflow.questions_30d",
           "stackoverflow.total_questions", "hackernews.stories_30d", "hackernews.points_30d"]
# slug: (latest values in METRICS order, past [repo_count, so_30d, hn_stories])
DATA = {
    "python": ([1_000_000, 2_000_000, 20_000, 2_200_000, 300, 5000], [980_000, 19_800, 295]),
    "react":  ([500_000, 1_600_000, 8_000, 460_000, 120, 2500],      [495_000, 7_900, 118]),
    "rust":   ([200_000, 900_000, 3_000, 45_000, 150, 4000],         [198_000, 2_950, 148]),
    "deno":   ([20_000, 150_000, 200, 5_000, 30, 400],               [15_000, 150, 20]),
    "bun":    ([5_000, 60_000, 40, 1_000, 10, 100],                  [3_000, 20, 5]),
}


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(session)
    yield session
    session.close()


def load(db, with_history=True):
    src = get_or_create_source(db, "test")
    for slug, (latest, past) in DATA.items():
        tid = resolve_technology(db, slug).id
        for metric, value in zip(METRICS, latest):
            db.add(MetricSnapshot(technology_id=tid, source_id=src.id, metric=metric, value=value, captured_on=TODAY))
        if with_history:
            for metric, value in zip(["github.repo_count", "stackoverflow.questions_30d", "hackernews.stories_30d"], past):
                db.add(MetricSnapshot(technology_id=tid, source_id=src.id, metric=metric, value=value, captured_on=PAST))
    db.commit()


def row(db, slug):
    return db.query(TechScore).filter_by(technology_id=resolve_technology(db, slug).id).one()


def test_percentile_ranks():
    r = percentile_ranks({1: 10, 2: 20, 3: 30})
    assert r == {1: 0.0, 2: 0.5, 3: 1.0}
    assert percentile_ranks({1: 5, 2: 5, 3: 9})[1] == 0.25  # ties share the average rank


def test_growth_rate_needs_history():
    assert growth_rate([(TODAY, 100)]) is None
    assert growth_rate([(TODAY - timedelta(days=3), 90), (TODAY, 100)]) is None  # under 7 days
    assert growth_rate([(TODAY - timedelta(days=30), 100), (TODAY, 150)]) == pytest.approx(0.5)


def test_score_order_without_history(db):
    load(db, with_history=False)
    out = compute_scores(db, today=TODAY)
    assert out == {"scored": 5, "with_growth": 0, "emerging": 0}
    scores = {s: row(db, s).devintel_score for s in DATA}
    assert scores["python"] > scores["react"] > scores["rust"] > scores["deno"] > scores["bun"]
    assert scores["python"] == 100 and scores["bun"] == 0
    assert all(row(db, s).growth_30d is None and not row(db, s).is_emerging for s in DATA)


def test_emerging_flag(db):
    load(db)
    out = compute_scores(db, today=TODAY)
    assert out["with_growth"] == 5 and out["emerging"] == 1
    assert row(db, "deno").is_emerging          # fast growth in all signals, not tiny
    assert row(db, "deno").growth_30d > 1.0
    assert not row(db, "bun").is_emerging       # fastest growth but lowest score -> excluded as too small
    assert not row(db, "python").is_emerging    # popular but slow growth


def test_rerun_is_idempotent(db):
    load(db)
    compute_scores(db, today=TODAY)
    compute_scores(db, today=TODAY)
    assert db.query(TechScore).count() == 5


def test_rankings_endpoints(db):
    load(db)
    compute_scores(db, today=TODAY)
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    top = c.get("/rankings/trending", params={"limit": 2}).json()
    assert [t["slug"] for t in top] == ["python", "react"]
    assert [t["slug"] for t in c.get("/rankings/emerging").json()] == ["deno"]
    detail = c.get("/technologies/deno").json()
    assert detail["is_emerging"] is True and detail["devintel_score"] is not None
    app.dependency_overrides.clear()
