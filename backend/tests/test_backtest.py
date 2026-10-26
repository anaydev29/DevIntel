from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.backtest import run_backtest, wilson
from app.collectors.base import get_or_create_source
from app.database import Base, get_db
from app.main import app
from app.models import MetricSnapshot, TechScore
from app.normalize import resolve_technology
from app.seed import seed

TODAY = date.today()
T0 = TODAY - timedelta(days=60)
SLUGS = ["python", "react", "django", "fastapi", "rust", "go"]


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(s)
    src = get_or_create_source(s, "t")
    for slug in SLUGS:
        tid = resolve_technology(s, slug).id
        for d in range(61):
            # Python really takes off from day 20 (+2% a day); everything else stays flat
            value = 1000 * (1.02 ** max(0, d - 20)) if slug == "python" else 1000
            s.add(MetricSnapshot(technology_id=tid, source_id=src.id, metric="github.repo_count", value=value, captured_on=T0 + timedelta(days=d)))
    s.commit()
    yield s
    s.close()


def flag(db, slug, day_offset):
    db.add(TechScore(technology_id=resolve_technology(db, slug).id, computed_on=T0 + timedelta(days=day_offset),
                     devintel_score=50, growth_30d=0.3, is_emerging=True))
    db.commit()


def test_wilson_interval():
    low, high = wilson(5, 10)
    assert (round(low, 3), round(high, 3)) == (0.237, 0.763)
    assert wilson(0, 0) == (None, None)
    low, high = wilson(10, 10)
    assert high == 1.0 and 0.70 < low < 0.75                                   # even 10 of 10 is not certainty


def test_hits_misses_and_repeated_flags_count_once(db):
    flag(db, "python", 20); flag(db, "python", 21)                              # same technology flagged two days in a row
    flag(db, "react", 20)                                                       # flagged, but never grows
    r = run_backtest(db, 14)
    assert r["status"] == "ready" and r["flags"] == 2 and r["hits"] == 1 and r["hit_rate"] == 0.5
    assert r["ci_low"] < 0.5 < r["ci_high"]
    by = {e["slug"]: e for e in r["events"]}
    assert by["python"]["beat_median"] is True and by["python"]["forward_growth"] == pytest.approx(1.02 ** 14 - 1)
    assert by["react"]["beat_median"] is False and by["react"]["forward_growth"] == 0   # flat is not "beating the median"
    assert r["avg_forward_growth_flagged"] == pytest.approx((1.02 ** 14 - 1) / 2)
    assert r["avg_forward_growth_all"] == pytest.approx((1.02 ** 14 - 1) / 6)           # the typical technology barely moved


def test_flags_that_are_too_recent_are_not_judged(db):
    flag(db, "python", 58)                                                       # 2 days ago: its 14-day outcome is unknown
    r = run_backtest(db, 14)
    assert r["status"] == "waiting" and r["flags"] == 0
    assert "none is 14 days old yet" in r["message"]


def test_no_flags_at_all_explains_when_a_result_can_appear(db):
    r = run_backtest(db, 14)
    assert r["status"] == "waiting" and "No technology has been flagged" in r["message"]
    assert (T0 + timedelta(days=7 + 14)).strftime("%d %b %Y") in r["message"]


def test_empty_database(db):
    db.query(MetricSnapshot).delete(); db.commit()
    assert run_backtest(db)["status"] == "no_data"


def test_endpoints(db):
    flag(db, "python", 20); flag(db, "react", 20)
    for slug in ("python", "react"):
        db.add(TechScore(technology_id=resolve_technology(db, slug).id, computed_on=TODAY, devintel_score=70, growth_30d=0.1, is_emerging=False))
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    body = c.get("/rankings/backtest", params={"horizon": 14}).json()
    assert body["status"] == "ready" and body["flags"] == 2 and body["events"][0]["flagged_on"] == (T0 + timedelta(days=20)).isoformat()
    assert c.get("/rankings/backtest", params={"horizon": 10}).status_code == 422
    h = c.get("/technologies/py/history", params={"days": 90}).json()                   # alias works
    assert h["slug"] == "python" and [p["value"] for p in h["score"]] == [50, 70]
    assert len(h["metrics"]["github.repo_count"]) == 61 and h["metrics"]["github.repo_count"][-1]["value"] > 1000
    assert c.get("/technologies/nope/history").status_code == 404
    assert c.get("/technologies/python/history", params={"days": 3}).status_code == 422
    app.dependency_overrides.clear()
