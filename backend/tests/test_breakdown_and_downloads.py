from datetime import date

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.analysis import SCORE_WEIGHTS, compute_scores
from app.collectors.base import get_or_create_source
from app.collectors.downloads import NPM_PACKAGES, PYPI_PACKAGES, NpmDownloadsCollector, PyPIDownloadsCollector
from app.database import Base, get_db
from app.main import app
from app.models import MetricSnapshot, ScoreComponent, Technology
from app.normalize import resolve_technology
from app.seed import seed

DATA = {"python": [1_000_000, 20_000, 300], "react": [500_000, 8_000, 120], "rust": [200_000, 3_000, 150], "deno": [20_000, 200, 30]}
METRICS = ["github.repo_count", "stackoverflow.questions_30d", "hackernews.stories_30d"]


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(s)
    yield s
    s.close()


def test_breakdown_explains_each_score_exactly(db):
    src = get_or_create_source(db, "t")
    for slug, vals in DATA.items():
        for metric, v in zip(METRICS, vals):
            db.add(MetricSnapshot(technology_id=resolve_technology(db, slug).id, source_id=src.id, metric=metric, value=v, captured_on=date.today()))
    db.commit()
    compute_scores(db)
    app.dependency_overrides[get_db] = lambda: db
    body = TestClient(app).get("/rankings/breakdown").json()
    app.dependency_overrides.clear()
    assert set(body["weights"]) == set(METRICS) and body["weights"]["stackoverflow.questions_30d"] == SCORE_WEIGHTS["stackoverflow.questions_30d"]
    assert [t["slug"] for t in body["technologies"]][0] == "python"                 # best first
    for t in body["technologies"]:
        total = sum(body["weights"][m] for m in t["components"])
        rebuilt = sum(body["weights"][m] / total * c["rank"] * 100 for m, c in t["components"].items())
        assert rebuilt == pytest.approx(t["devintel_score"], abs=0.05), t["slug"]   # the bars add up to the score
    assert body["technologies"][0]["components"]["github.repo_count"] == {"value": 1_000_000, "rank": 1.0}


def test_components_are_replaced_not_duplicated_on_rerun(db):
    src = get_or_create_source(db, "t")
    for slug, vals in DATA.items():
        for metric, v in zip(METRICS, vals):
            db.add(MetricSnapshot(technology_id=resolve_technology(db, slug).id, source_id=src.id, metric=metric, value=v, captured_on=date.today()))
    db.commit()
    compute_scores(db); compute_scores(db)
    assert db.query(ScoreComponent).count() == len(DATA) * len(METRICS)


def test_breakdown_before_first_analysis_is_empty(db):
    app.dependency_overrides[get_db] = lambda: db
    body = TestClient(app).get("/rankings/breakdown").json()
    app.dependency_overrides.clear()
    assert body == {"computed_on": None, "weights": {}, "technologies": []}


def make_downloads(handler, cls):
    return cls(client=httpx.Client(transport=httpx.MockTransport(handler)), delay=0)


def values(db, metric):
    return {db.get(Technology, m.technology_id).slug: m.value for m in db.query(MetricSnapshot).filter_by(metric=metric)}


def test_npm_collector_covers_only_mapped_technologies(db):
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(200, json={"downloads": 1234})
    run = make_downloads(handler, NpmDownloadsCollector).run(db)
    assert run.status == "success" and run.records_fetched == len(NPM_PACKAGES) == 7
    assert set(values(db, "npm.downloads_week")) == set(NPM_PACKAGES)
    assert "/downloads/point/last-week/@angular/core" in seen                       # scoped package name is passed through
    assert not any("redis" in p or "mongodb" in p for p in seen)                    # client libraries are not the technology


def test_pypi_collector_maps_pytorch_to_torch(db):
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(200, json={"data": {"last_day": 1, "last_week": 777, "last_month": 3000}})
    run = make_downloads(handler, PyPIDownloadsCollector).run(db)
    assert run.status == "success" and run.records_fetched == len(PYPI_PACKAGES) == 6
    assert values(db, "pypi.downloads_week")["pytorch"] == 777
    assert "/api/packages/torch/recent" in seen


def test_download_errors_are_logged_and_rate_limits_stop_the_run(db):
    def missing(request):
        return httpx.Response(404) if "svelte" in request.url.path else httpx.Response(200, json={"downloads": 5})
    run = make_downloads(missing, NpmDownloadsCollector).run(db)
    assert run.status == "partial" and run.error_count == 1 and "svelte" in run.error_log
    run = make_downloads(lambda r: httpx.Response(429), PyPIDownloadsCollector).run(db)
    assert run.status == "failed" and run.error_count == 1                           # stopped at once instead of hammering the API
