import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.collectors.github import GitHubCollector
from app.database import Base
from app.models import MetricSnapshot, Repository, Technology
from app.seed import seed


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(s)
    yield s
    s.close()


def collector(handler):
    c = GitHubCollector(token="test-token")
    c.client = httpx.Client(transport=httpx.MockTransport(handler))
    c.delay = 0
    return c


def repo(i, stars, forks):
    return {"id": i, "full_name": f"org/repo{i}", "stargazers_count": stars, "forks_count": forks, "language": "Python",
            "topics": ["python"], "created_at": "2024-01-02T03:04:05Z"}


def values(db, metric):
    return {db.get(Technology, m.technology_id).slug: m.value for m in db.query(MetricSnapshot).filter_by(metric=metric)}


def test_saves_counts_and_top_repositories_and_uses_topic_overrides(db):
    queries = []

    def handler(request):
        queries.append(request.url.params["q"])
        return httpx.Response(200, json={"total_count": 1234, "items": [repo(1, 500, 50), repo(2, 300, 20)]})
    run = collector(handler).run(db, only_slugs=["python", "go"])
    assert run.status == "success" and run.records_fetched == 10                      # (3 metrics + 2 repos) x 2 technologies
    assert values(db, "github.repo_count") == {"python": 1234, "go": 1234}
    assert values(db, "github.top_stars")["python"] == 800 and values(db, "github.top_forks")["python"] == 70
    assert sorted(queries) == ["topic:golang", "topic:python"]                          # Go is searched as "golang"
    assert db.query(Repository).count() == 2 and db.query(Repository).first().created_at_gh.year == 2024


def test_rerunning_updates_instead_of_duplicating(db):
    stars = {"n": 500}

    def handler(request):
        return httpx.Response(200, json={"total_count": 10, "items": [repo(1, stars["n"], 5)]})
    c = collector(handler)
    c.run(db, only_slugs=["python"])
    stars["n"] = 900
    c.run(db, only_slugs=["python"])
    assert db.query(MetricSnapshot).filter_by(metric="github.top_stars").count() == 1
    assert db.query(Repository).one().stars == 900


def test_rate_limit_stops_the_run_and_other_errors_do_not(db):
    run = collector(lambda r: httpx.Response(403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1"})).run(
        db, only_slugs=["python", "react", "vue"])
    assert run.status == "failed" and run.error_count == 1                             # stopped at once

    def handler(request):
        return httpx.Response(500) if "topic:react" in request.url.params["q"] else httpx.Response(200, json={"total_count": 1, "items": []})
    run = collector(handler).run(db, only_slugs=["python", "react", "vue"])
    assert run.status == "partial" and run.error_count == 1 and "react" in run.error_log   # one bad technology does not stop the rest
    assert set(values(db, "github.repo_count")) == {"python", "vue"}
