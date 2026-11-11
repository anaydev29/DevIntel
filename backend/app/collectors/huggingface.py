"""Hugging Face collector: what is trending in open-source AI, and how popular the big AI libraries are.

Uses the public Hugging Face Hub API. No key is needed; set HF_TOKEN in backend/.env for a higher rate limit.

Saved every day
- hub_items            the 20 trending models, 20 trending datasets and 20 trending spaces, in rank order
                       (Hugging Face's own "trendingScore" measures current momentum, not all-time popularity)
- huggingface.top_downloads_30d   for technologies that are Hub library tags (PyTorch, TensorFlow): the downloads of
                       the last 30 days summed over the 100 most-downloaded models carrying that library tag

Each section is fetched on its own, so a failure in one does not lose the others (the run is marked "partial").
"""
import time
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import save_metric
from app.collectors.hub_base import SectionsCollector, TechLinker, check_status, clip, to_int, upsert_hub_item
from app.models import Source, Technology
from app.secrets_util import get_secret

API = "https://huggingface.co/api"
TRENDING_LIMIT = 20
LIBRARY_TAGS = {"pytorch": "pytorch", "tensorflow": "tensorflow"}   # catalog slug -> Hub library tag
KIND = {"models": "model", "datasets": "dataset", "spaces": "space"}
URL_PREFIX = {"models": "", "datasets": "datasets/", "spaces": "spaces/"}
EXPAND = {
    "models": ["downloads", "likes", "trendingScore", "pipeline_tag", "library_name", "tags", "createdAt"],
    "datasets": ["downloads", "likes", "trendingScore", "tags", "createdAt", "description"],
    "spaces": ["likes", "trendingScore", "tags", "createdAt", "sdk"],
}
NOISE_TAGS = {"endpoints_compatible", "autotrain_compatible", "text-generation-inference"}


def readable_tags(tags: list) -> list[str]:
    """Plain tags only: drop 'license:mit', 'arxiv:...', 'region:us' and similar technical labels."""
    return [t for t in tags if isinstance(t, str) and ":" not in t and t not in NOISE_TAGS]


class HuggingFaceCollector(SectionsCollector):
    source_name = "huggingface"

    def _headers(self) -> dict:
        token = get_secret("HF_TOKEN")
        return {"Authorization": f"Bearer {token}"} if token else {}

    def _list(self, endpoint: str, params: dict, expand: list[str]) -> list[dict]:
        query = list(params.items()) + [("expand[]", field) for field in expand]
        resp = self.client.get(f"{API}/{endpoint}", params=query, headers=self._headers())
        if resp.status_code == 400 and expand:        # a field name was refused: ask for the default fields
            resp = self.client.get(f"{API}/{endpoint}", params=list(params.items()), headers=self._headers())
        check_status(resp, f"huggingface {endpoint}")
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError("unexpected response from the Hub API")
        return data

    def sections(self):
        sections = [(endpoint, self._trending(endpoint)) for endpoint in ("models", "datasets", "spaces")]
        sections.append(("library downloads", self._libraries))
        return sections

    def _trending(self, endpoint: str):
        def fetch(db: Session, source: Source, day: date) -> int:
            items = self._list(endpoint, {"sort": "trendingScore", "direction": "-1", "limit": str(TRENDING_LIMIT)},
                               EXPAND[endpoint])
            linker = TechLinker(db)
            saved = 0
            for item in items:
                external_id = item.get("id") or item.get("modelId")
                if not external_id:
                    continue
                saved += 1
                all_tags = [t for t in (item.get("tags") or []) if isinstance(t, str)]
                library = item.get("library_name")
                extra = {"created_at": item.get("createdAt")}
                description = None
                if endpoint == "models":
                    extra.update(pipeline_tag=item.get("pipeline_tag"), library=library)
                elif endpoint == "datasets":
                    task = next((t.split(":", 1)[1] for t in all_tags if t.startswith("task_categories:")), None)
                    extra.update(task=task)
                    description = clip(item.get("description"), 400)
                else:
                    extra.update(sdk=item.get("sdk"))
                trending = item.get("trendingScore")
                upsert_hub_item(
                    db, self.source_name, KIND[endpoint], external_id, day,
                    rank=saved, title=external_id, url=f"https://huggingface.co/{URL_PREFIX[endpoint]}{external_id}",
                    author=external_id.split("/")[0] if "/" in external_id else None,
                    description=description, tags=readable_tags(all_tags)[:6],
                    downloads=to_int(item.get("downloads")), likes=to_int(item.get("likes")),
                    trending_score=float(trending) if trending is not None else None, extra=extra,
                    technology_id=linker.link(([library] if library else []) + all_tags),
                )
            time.sleep(self.delay)
            return saved
        return fetch

    def _libraries(self, db: Session, source: Source, day: date) -> int:
        saved = 0
        for slug, tag in LIBRARY_TAGS.items():
            tech = db.scalar(select(Technology).where(Technology.slug == slug))
            if tech is None:
                continue
            models = self._list("models", {"filter": tag, "sort": "downloads", "direction": "-1", "limit": "100"},
                                ["downloads"])
            save_metric(db, tech.id, source.id, "huggingface.top_downloads_30d",
                        sum(to_int(m.get("downloads")) for m in models), day)
            saved += 1
            time.sleep(self.delay)
        return saved
