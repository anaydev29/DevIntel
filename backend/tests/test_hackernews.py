import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.collectors.hackernews import HackerNewsCollector
from app.database import Base
from app.models import MetricSnapshot
from app.seed import seed


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(session)
    yield session
    session.close()


def collector(handler):
    return HackerNewsCollector(client=httpx.Client(transport=httpx.MockTransport(handler)), delay=0)


def test_collects_stories_and_points(db):
    seen = {}

    def handler(request):
        seen["query"] = request.url.params["query"]
        return httpx.Response(200, json={"nbHits": 42, "hits": [{"points": 100}, {"points": None}, {"points": 25}]})

    run = collector(handler).run(db, only_slugs=["go"])
    assert run.status == "success" and run.records_fetched == 2
    assert seen["query"] == "golang"  # ambiguous name uses the override
    vals = {m.metric: m.value for m in db.query(MetricSnapshot).all()}
    assert vals == {"hackernews.stories_30d": 42, "hackernews.points_30d": 125}


def test_rate_limit_stops_run(db):
    run = collector(lambda r: httpx.Response(429)).run(db, only_slugs=["python", "react"])
    assert run.status == "failed" and run.error_count == 1
