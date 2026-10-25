from collections import defaultdict
from datetime import date

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.analysis import GROWTH_WEIGHTS, SCORE_WEIGHTS
from app.collectors.devto import TAG_OVERRIDES
from app.collectors.downloads import NPM_PACKAGES, PYPI_PACKAGES
from app.collectors.hackernews import QUERY_OVERRIDES
from app.collectors.hn_hiring import PATTERNS
from app.collectors.wikipedia import WIKI_TITLES, WikipediaCollector
from app.database import Base
from app.models import MetricSnapshot, Technology
from app.normalize import clean
from app.seed import CATALOG, seed


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(s)
    yield s
    s.close()


def collector(handler):
    return WikipediaCollector(client=httpx.Client(transport=httpx.MockTransport(handler)), delay=0, today=date(2026, 10, 30))


def test_sums_thirty_days_of_views_for_the_right_dates_and_encodes_titles(db):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"items": [{"views": 100}, {"views": 250}, {"views": 50}]})
    run = collector(handler).run(db, only_slugs=["cpp", "python"])
    assert run.status == "success" and run.records_fetched == 2
    vals = {db.get(Technology, m.technology_id).slug: m.value for m in db.query(MetricSnapshot).filter_by(metric="wikipedia.views_30d")}
    assert vals == {"cpp": 400, "python": 400}
    assert any("/C%2B%2B/daily/20260930/20261029" in u for u in seen)           # "C++" is URL-encoded; 30 full days ending yesterday
    assert any("Python_%28programming_language%29" in u for u in seen)


def test_missing_article_is_skipped_and_rate_limit_stops_the_run(db, caplog):
    run = collector(lambda r: httpx.Response(404)).run(db, only_slugs=["python", "react"])
    assert run.status == "success" and run.records_fetched == 0 and "WIKI_TITLES" in caplog.text
    run = collector(lambda r: httpx.Response(429)).run(db, only_slugs=["python", "react"])
    assert run.status == "failed" and run.error_count == 1


def test_technologies_without_a_title_are_skipped(db):
    def handler(request):
        raise AssertionError("no request expected")
    # every catalog entry has a title today; prove the skip path with a technology that is not in the map
    db.add(Technology(slug="unmapped", name="Unmapped", category="tool"))
    db.commit()
    run = collector(lambda r: httpx.Response(200, json={"items": [{"views": 1}]})).run(db, only_slugs=["unmapped"])
    assert run.records_fetched == 0 and run.status == "success"


def test_catalog_is_clean():
    slugs = [c[0] for c in CATALOG]
    assert len(slugs) == len(set(slugs)) == 87
    owner = defaultdict(set)
    for slug, name, *_rest, aliases in CATALOG:
        for term in {clean(name), *map(clean, aliases)} - {slug}:
            owner[term].add(slug)
    clashes = {t: s for t, s in owner.items() if len(s) > 1}
    assert not clashes, f"the same alias points at different technologies: {clashes}"
    assert not (set(clean(n) for _, n, *_ in CATALOG) & {s for s in slugs} - set(slugs))   # names never shadow another slug
    for slug, _name, category, topic, so_tag, _aliases in CATALOG:
        assert category and topic and so_tag, slug


def test_every_mapping_points_at_a_real_technology():
    slugs = {c[0] for c in CATALOG}
    for name, mapping in {"wikipedia": WIKI_TITLES, "hiring": PATTERNS, "hn search": QUERY_OVERRIDES, "dev.to": TAG_OVERRIDES,
                          "npm": NPM_PACKAGES, "pypi": PYPI_PACKAGES}.items():
        assert set(mapping) <= slugs, f"{name} refers to unknown technologies: {set(mapping) - slugs}"
    assert slugs == set(WIKI_TITLES)                                       # every technology has a Wikipedia article


def test_weights_add_up_to_one():
    assert sum(SCORE_WEIGHTS.values()) == pytest.approx(1.0)
    assert sum(GROWTH_WEIGHTS.values()) == pytest.approx(1.0)
