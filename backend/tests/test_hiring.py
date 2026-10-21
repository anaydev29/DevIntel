import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.collectors.hn_hiring import HackerNewsHiringCollector, count_mentions
from app.database import Base
from app.models import MetricSnapshot, Technology
from app.seed import seed


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(session)
    yield session
    session.close()


def test_count_mentions_rules():
    posts = [
        "Acme | Python, Django, <a href='https://boards.greenhouse.io/rust-labs'>apply</a> | Remote",
        "Beta | JavaScript and React.js | Berlin",           # Java must NOT match JavaScript
        "Gamma | Senior Java developer, Postgres, Kubernetes",
        "Delta | C++ and Golang, k8s, SwiftUI",
        "Epsilon | we swiftly move fast and go far",         # lowercase swift / plain go: no match
        "Zeta | React Native, NodeJS, TypeScript, Next.js",
    ]
    c = count_mentions(posts)
    assert c["python"] == 1 and c["django"] == 1
    assert c["javascript"] == 1 and c["java"] == 1            # exactly one post each
    assert c["react"] == 2 and c["nodejs"] == 1 and c["nextjs"] == 1
    assert c["cpp"] == 1 and c["go"] == 1 and c["swift"] == 1
    assert c["kubernetes"] == 2 and c["postgresql"] == 1
    assert c["rust"] == 0                                      # only appeared inside a link, which is removed


def thread(oid, title, n_posts, mention="Python"):
    return {"objectID": oid, "title": title}, {"children": [{"text": f"Company {i} | {mention} | Remote"} for i in range(n_posts)]}


def make_handler(threads):
    items = {t[0]["objectID"]: t[1] for t in threads}

    def handler(request):
        if request.url.path.endswith("/search_by_date"):
            hits = [t[0] for t in threads] + [{"objectID": "x", "title": "Ask HN: Who wants to be hired? (October 2026)"}]
            return httpx.Response(200, json={"hits": hits})
        return httpx.Response(200, json=items[request.url.path.rsplit("/", 1)[1]])
    return handler


def run(db, threads):
    client = httpx.Client(transport=httpx.MockTransport(make_handler(threads)))
    return HackerNewsHiringCollector(client=client).run(db)


def metric(db, slug, name):
    tid = db.query(Technology).filter_by(slug=slug).one().id
    return db.query(MetricSnapshot).filter_by(technology_id=tid, metric=name).one().value


def test_saves_mentions_and_share(db):
    run_obj = run(db, [thread("1", "Ask HN: Who is hiring? (October 2026)", 200)])
    assert run_obj.status == "success"
    assert metric(db, "python", "hiring.mentions") == 200 and metric(db, "python", "hiring.share_pct") == 100
    assert metric(db, "rust", "hiring.share_pct") == 0


def test_new_small_thread_falls_back_to_previous_month(db):
    new = thread("2", "Ask HN: Who is hiring? (November 2026)", 10, mention="Rust")        # just posted: too few posts
    old = thread("1", "Ask HN: Who is hiring? (October 2026)", 200, mention="Python")
    run(db, [new, old])
    assert metric(db, "python", "hiring.mentions") == 200                                     # used October
    assert metric(db, "rust", "hiring.mentions") == 0


def test_no_thread_is_a_logged_failure(db):
    handler = lambda r: httpx.Response(200, json={"hits": []})  # noqa: E731
    run_obj = HackerNewsHiringCollector(client=httpx.Client(transport=httpx.MockTransport(handler))).run(db)
    assert run_obj.status == "failed" and "no 'Who is hiring?' thread" in run_obj.error_log
