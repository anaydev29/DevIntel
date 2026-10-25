import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.collectors.stackoverflow import StackOverflowCollector
from app.database import Base
from app.models import MetricSnapshot, PipelineRun
from app.seed import seed


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(session)
    yield session
    session.close()


def make_collector(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return StackOverflowCollector(key="test", client=client, delay=0)


def fake_api(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/info"):
        if "python" in path and "python3" not in path:
            return httpx.Response(200, json={"items": [{"name": "python", "count": 2200000}], "quota_remaining": 250})
        return httpx.Response(200, json={"items": [], "quota_remaining": 250})  # unknown tag
    return httpx.Response(200, json={"total": 18000, "quota_remaining": 249})


def test_collects_two_metrics(db):
    run = make_collector(fake_api).run(db, only_slugs=["python"])
    assert run.status == "success" and run.records_fetched == 2
    vals = {m.metric: m.value for m in db.query(MetricSnapshot).all()}
    assert vals == {"stackoverflow.total_questions": 2200000, "stackoverflow.questions_30d": 18000}


def test_unknown_tag_is_skipped_with_a_warning(db, caplog):
    run = make_collector(fake_api).run(db, only_slugs=["python", "react"])
    assert run.status == "success" and run.error_count == 0 and run.records_fetched == 2     # react's tag is missing: skipped, not failed
    assert "reactjs" in caplog.text                                                             # but the log says which tag to fix


def test_quota_exhausted_stops_run(db):
    def throttled(request):
        return httpx.Response(400, json={"error_id": 502, "error_message": "too many requests"})
    run = make_collector(throttled).run(db, only_slugs=["python", "react", "vue"])
    assert run.status == "failed" and run.error_count == 1  # stopped after first, did not hammer the API
    assert db.query(PipelineRun).count() == 1
