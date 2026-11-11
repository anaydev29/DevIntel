from datetime import date, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.collectors.huggingface import HuggingFaceCollector, readable_tags
from app.collectors.kaggle import KaggleCollector, as_list
from app.database import Base, get_db
from app.main import app
from app.models import MetricSnapshot, Technology
from app.models_hub import HubItem
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
def secrets(monkeypatch):
    """Secrets the collectors can see; tests set them here instead of reading backend/.env."""
    values: dict = {}
    monkeypatch.setattr("app.collectors.kaggle.get_secret", lambda name: values.get(name))
    monkeypatch.setattr("app.collectors.huggingface.get_secret", lambda name: values.get(name))
    return values


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


# ----------------------------------------------------------------------- Hugging Face
MODELS = [
    {"id": "meta/llama", "downloads": 1000, "likes": 50, "trendingScore": 120.5, "pipeline_tag": "text-generation",
     "library_name": "transformers", "createdAt": "2026-10-01T00:00:00.000Z",
     "tags": ["pytorch", "license:mit", "text-generation", "endpoints_compatible"]},
    {"id": "solo-model", "downloads": 10, "likes": 1, "trendingScore": 5, "tags": []},
]
DATASETS = [{"id": "org/data", "downloads": 70, "likes": 9, "trendingScore": 3,
             "tags": ["task_categories:translation", "language:en"], "description": "A  big\ndataset"}]
SPACES = [{"id": "me/demo", "likes": 4, "trendingScore": 2, "sdk": "gradio", "tags": ["gradio"]}]


def hf_ok(request):
    path, params = request.url.path, dict(request.url.params)
    if path == "/api/models" and params.get("filter"):
        return httpx.Response(200, json=[{"id": "a/b", "downloads": 100}, {"id": "c/d", "downloads": 50}])
    return httpx.Response(200, json={"/api/models": MODELS, "/api/datasets": DATASETS, "/api/spaces": SPACES}[path])


def test_huggingface_saves_trending_items_and_library_downloads(db):
    run = HuggingFaceCollector(client=client_for(hf_ok), delay=0).run(db)
    assert run.status == "success" and run.error_count == 0

    models = db.query(HubItem).filter_by(kind="model").order_by(HubItem.rank).all()
    assert [m.title for m in models] == ["meta/llama", "solo-model"] and models[0].rank == 1
    top = models[0]
    assert top.url == "https://huggingface.co/meta/llama" and top.author == "meta"
    assert top.downloads == 1000 and top.likes == 50 and top.trending_score == 120.5
    assert top.tags == ["pytorch", "text-generation"]                    # technical labels are dropped
    assert top.extra["pipeline_tag"] == "text-generation" and top.extra["library"] == "transformers"
    assert db.get(Technology, top.technology_id).slug == "pytorch"       # linked through its "pytorch" tag
    assert models[1].technology_id is None and models[1].author is None

    dataset = db.query(HubItem).filter_by(kind="dataset").one()
    assert dataset.url == "https://huggingface.co/datasets/org/data" and dataset.description == "A big dataset"
    assert dataset.extra["task"] == "translation"
    space = db.query(HubItem).filter_by(kind="space").one()
    assert space.url == "https://huggingface.co/spaces/me/demo" and space.extra["sdk"] == "gradio"

    totals = {db.get(Technology, m.technology_id).slug: m.value for m in
              db.query(MetricSnapshot).filter_by(metric="huggingface.top_downloads_30d")}
    assert totals == {"pytorch": 150, "tensorflow": 150}


def test_huggingface_rerun_does_not_duplicate(db):
    for _ in range(2):
        HuggingFaceCollector(client=client_for(hf_ok), delay=0).run(db)
    assert db.query(HubItem).count() == 4
    assert db.query(MetricSnapshot).filter_by(metric="huggingface.top_downloads_30d").count() == 2


def test_huggingface_retries_without_fields_when_a_field_is_refused(db):
    def handler(request):
        if "expand" in request.url.query.decode():
            return httpx.Response(400, json={"error": "bad field"})
        return hf_ok(request)

    run = HuggingFaceCollector(client=client_for(handler), delay=0).run(db)
    assert run.status == "success" and db.query(HubItem).filter_by(kind="model").count() == 2


def test_one_failing_section_makes_the_run_partial(db):
    def handler(request):
        if request.url.path == "/api/spaces":
            return httpx.Response(500)
        return hf_ok(request)

    run = HuggingFaceCollector(client=client_for(handler), delay=0).run(db)
    assert run.status == "partial" and run.error_count == 1 and "spaces" in run.error_log
    assert db.query(HubItem).filter_by(kind="model").count() == 2          # the other sections were kept
    assert db.query(HubItem).filter_by(kind="space").count() == 0


def test_all_sections_failing_is_a_failed_run(db):
    run = HuggingFaceCollector(client=client_for(lambda r: httpx.Response(500)), delay=0).run(db)
    assert run.status == "failed" and run.records_fetched == 0


def test_rate_limit_is_reported(db):
    run = HuggingFaceCollector(client=client_for(lambda r: httpx.Response(429)), delay=0).run(db)
    assert run.status == "failed" and "rate limited" in run.error_log


def test_readable_tags():
    assert readable_tags(["pytorch", "license:mit", "arxiv:1", "endpoints_compatible", 5, "nlp"]) == ["pytorch", "nlp"]


# ----------------------------------------------------------------------- Kaggle
DATASET = {"ref": "owner/ds", "title": "Titanic", "subtitle": "who survived", "creatorName": "Owner",
           "url": "https://www.kaggle.com/datasets/owner/ds", "downloadCount": 1000, "voteCount": 50,
           "usabilityRating": 0.94, "tags": [{"name": "python"}, {"name": "beginner"}], "totalBytes": 1234, "viewCount": 9}
KERNEL = {"ref": "u/nb", "title": "EDA", "author": "U", "totalVotes": 12, "language": "python",
          "kernelType": "notebook", "lastRunTime": "2026-10-01"}
COMPETITION = {"ref": "https://www.kaggle.com/competitions/titanic", "title": "Titanic", "description": "Predict survival",
               "reward": "Knowledge", "deadline": "2030-01-01 00:00:00", "teamCount": 14000, "category": "Getting Started"}


def kaggle_handler(seen=None):
    def handler(request):
        if seen is not None:
            seen.append((request.url.path, request.headers.get("authorization")))
        data = {"/api/v1/datasets/list": [DATASET], "/api/v1/kernels/list": [KERNEL],
                "/api/v1/competitions/list": [COMPETITION]}[request.url.path]
        return httpx.Response(200, json=data)
    return handler


def test_kaggle_with_username_and_key(db, secrets):
    secrets.update(KAGGLE_USERNAME="me", KAGGLE_KEY="secret")
    seen: list = []
    run = KaggleCollector(client=client_for(kaggle_handler(seen)), delay=0).run(db)
    assert run.status == "success"
    assert len(seen) == 3 and all(auth and auth.startswith("Basic ") for _, auth in seen)

    dataset = db.query(HubItem).filter_by(kind="dataset").one()
    assert dataset.title == "Titanic" and dataset.likes == 50 and dataset.downloads == 1000
    assert dataset.tags == ["python", "beginner"] and dataset.extra["usability"] == 0.94
    assert db.get(Technology, dataset.technology_id).slug == "python"
    notebook = db.query(HubItem).filter_by(kind="notebook").one()
    assert notebook.likes == 12 and notebook.url == "https://www.kaggle.com/code/u/nb" and notebook.author == "U"
    competition = db.query(HubItem).filter_by(kind="competition").one()
    assert competition.external_id == "titanic" and competition.extra["teams"] == 14000
    assert competition.url == "https://www.kaggle.com/competitions/titanic"


def test_kaggle_with_an_api_token(db, secrets):
    secrets["KAGGLE_API_TOKEN"] = "KGAT_abc"
    seen: list = []
    KaggleCollector(client=client_for(kaggle_handler(seen)), delay=0).run(db)
    assert seen and all(auth == "Bearer KGAT_abc" for _, auth in seen)


def test_kaggle_without_credentials_only_collects_datasets(db, secrets):
    seen: list = []
    run = KaggleCollector(client=client_for(kaggle_handler(seen)), delay=0).run(db)
    assert run.status == "success"
    assert [path for path, _ in seen] == ["/api/v1/datasets/list"] and all(auth is None for _, auth in seen)
    assert {i.kind for i in db.query(HubItem)} == {"dataset"}


def test_kaggle_asks_for_credentials_when_refused(db, secrets):
    run = KaggleCollector(client=client_for(lambda r: httpx.Response(401)), delay=0).run(db)
    assert run.status == "failed" and "credentials" in run.error_log


def test_kaggle_rejected_credentials(db, secrets):
    secrets.update(KAGGLE_USERNAME="me", KAGGLE_KEY="wrong")
    run = KaggleCollector(client=client_for(lambda r: httpx.Response(403)), delay=0).run(db)
    assert run.status == "failed" and "rejected" in run.error_log


def test_as_list_accepts_a_wrapped_list():
    assert as_list({"datasets": [{"ref": "a"}]}) == [{"ref": "a"}]
    assert as_list([{"ref": "a"}, "junk"]) == [{"ref": "a"}]
    with pytest.raises(ValueError):
        as_list("nope")


# ----------------------------------------------------------------------- API
@pytest.fixture()
def api(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def add(db, day, kind, rank, title, source="huggingface", tech=None):
    db.add(HubItem(source=source, kind=kind, external_id=f"{kind}-{title}", captured_on=day, rank=rank, title=title,
                   url=f"https://x.test/{title}", tags=["a"], downloads=rank, likes=1, extra={}, technology_id=tech))


def test_hub_api_returns_the_newest_snapshot_in_rank_order(db, api):
    assert api.get("/hub/items").json() == [] and api.get("/hub/summary").json() == []
    today, yesterday = date.today(), date.today() - timedelta(days=1)
    torch_id = db.query(Technology).filter_by(slug="pytorch").one().id
    add(db, yesterday, "model", 1, "old-model")
    for rank, title in [(2, "second"), (1, "first"), (3, "third")]:
        add(db, today, "model", rank, title, tech=torch_id if title == "first" else None)
    add(db, today, "dataset", 1, "ds")
    add(db, today, "competition", 1, "comp", source="kaggle")
    db.commit()

    models = api.get("/hub/items", params={"kind": "model"}).json()
    assert [m["title"] for m in models] == ["first", "second", "third"]          # yesterday's snapshot is ignored
    assert models[0]["technology"] == "pytorch" and models[1]["technology"] is None
    assert [m["title"] for m in api.get("/hub/items", params={"kind": "model", "limit": 2}).json()] == ["first", "second"]
    assert {i["source"] for i in api.get("/hub/items").json()} == {"huggingface", "kaggle"}
    assert [i["title"] for i in api.get("/hub/items", params={"source": "kaggle"}).json()] == ["comp"]
    assert api.get("/hub/items", params={"kind": "movie"}).status_code == 422

    summary = {(r["source"], r["kind"]): r["items"] for r in api.get("/hub/summary").json()}
    assert summary == {("huggingface", "model"): 3, ("huggingface", "dataset"): 1, ("kaggle", "competition"): 1}
