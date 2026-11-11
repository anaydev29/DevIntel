"""Kaggle collector: hot datasets, popular notebooks and competitions.

Uses the Kaggle public API (https://www.kaggle.com/api/v1).
- Datasets: work without an account, but an account is better.
- Notebooks and competitions: need credentials; without them those two sections are simply skipped.

Credentials (put them in backend/.env, and in the GitHub repository secrets for the daily workflow):
  KAGGLE_USERNAME and KAGGLE_KEY      from kaggle.com/settings -> API -> "Create New Token" (the kaggle.json file)
  or KAGGLE_API_TOKEN                 a newer-style token ("KGAT_...")
"""
import time
from datetime import date

import httpx
from sqlalchemy.orm import Session

from app.collectors.hub_base import SectionsCollector, TechLinker, check_status, clip, to_int, upsert_hub_item
from app.models import Source
from app.secrets_util import get_secret

API = "https://www.kaggle.com/api/v1"
LIMIT = 20


def as_list(data) -> list[dict]:
    if isinstance(data, dict):  # some versions wrap the list in an object
        data = next((v for v in data.values() if isinstance(v, list)), [])
    if not isinstance(data, list):
        raise ValueError("unexpected response from Kaggle")
    return [d for d in data if isinstance(d, dict)]


def tag_names(tags) -> list[str]:
    names = [t.get("name") if isinstance(t, dict) else t for t in (tags or [])]
    return [str(n) for n in names if n]


class KaggleCollector(SectionsCollector):
    source_name = "kaggle"

    def credentials(self) -> tuple[dict, httpx.Auth | None]:
        token = get_secret("KAGGLE_API_TOKEN")
        if token:
            return {"Authorization": f"Bearer {token}"}, None
        user, key = get_secret("KAGGLE_USERNAME"), get_secret("KAGGLE_KEY")
        if user and key:
            return {}, httpx.BasicAuth(user, key)
        return {}, None

    def has_credentials(self) -> bool:
        headers, auth = self.credentials()
        return bool(headers or auth)

    def _get(self, path: str, params: dict) -> list[dict]:
        headers, auth = self.credentials()
        resp = self.client.get(f"{API}/{path}", params=params, headers=headers, auth=auth)
        if resp.status_code in (401, 403):
            raise ValueError("Kaggle rejected the credentials" if (headers or auth) else
                             "Kaggle needs credentials: set KAGGLE_USERNAME and KAGGLE_KEY (or KAGGLE_API_TOKEN) in backend/.env")
        check_status(resp, f"kaggle {path}")
        return as_list(resp.json())

    def sections(self):
        sections = [("datasets", self._datasets)]
        if self.has_credentials():
            sections += [("notebooks", self._notebooks), ("competitions", self._competitions)]
        return sections

    def _datasets(self, db: Session, source: Source, day: date) -> int:
        items = self._get("datasets/list", {"sortBy": "hottest", "page": 1})[:LIMIT]
        linker = TechLinker(db)
        for rank, d in enumerate(items, start=1):
            ref = d.get("ref") or ""
            tags = tag_names(d.get("tags"))
            upsert_hub_item(
                db, self.source_name, "dataset", ref, day, rank=rank, title=d.get("title") or ref,
                url=d.get("url") or f"https://www.kaggle.com/datasets/{ref}",
                author=d.get("creatorName") or d.get("ownerName") or (ref.split("/")[0] if "/" in ref else None),
                description=clip(d.get("subtitle") or d.get("description"), 400), tags=tags[:6],
                downloads=to_int(d.get("downloadCount")), likes=to_int(d.get("voteCount")),
                extra={"usability": d.get("usabilityRating"), "views": to_int(d.get("viewCount")),
                       "size_bytes": to_int(d.get("totalBytes")), "updated": str(d.get("lastUpdated") or "") or None},
                technology_id=linker.link(tags),
            )
        time.sleep(self.delay)
        return len(items)

    def _notebooks(self, db: Session, source: Source, day: date) -> int:
        items = self._get("kernels/list", {"sortBy": "hotness", "pageSize": LIMIT, "page": 1})[:LIMIT]
        for rank, d in enumerate(items, start=1):
            ref = d.get("ref") or ""
            upsert_hub_item(
                db, self.source_name, "notebook", ref, day, rank=rank, title=d.get("title") or ref,
                url=d.get("url") or f"https://www.kaggle.com/code/{ref}",
                author=d.get("author") or (ref.split("/")[0] if "/" in ref else None),
                description=None, tags=[], downloads=0, likes=to_int(d.get("totalVotes") or d.get("voteCount")),
                extra={"language": d.get("language"), "kernel_type": d.get("kernelType"),
                       "last_run": str(d.get("lastRunTime") or "") or None},
            )
        time.sleep(self.delay)
        return len(items)

    def _competitions(self, db: Session, source: Source, day: date) -> int:
        items = self._get("competitions/list", {"sortBy": "numberOfTeams", "page": 1})[:LIMIT]
        for rank, d in enumerate(items, start=1):
            slug = (d.get("ref") or "").rstrip("/").split("/")[-1]
            upsert_hub_item(
                db, self.source_name, "competition", slug, day, rank=rank, title=d.get("title") or slug,
                url=d.get("url") or f"https://www.kaggle.com/competitions/{slug}",
                author=d.get("organizationName"), description=clip(d.get("description"), 400),
                tags=tag_names(d.get("tags"))[:6], downloads=0, likes=0,
                extra={"reward": d.get("reward"), "deadline": str(d.get("deadline") or "") or None,
                       "teams": to_int(d.get("teamCount")), "category": d.get("category")},
            )
        time.sleep(self.delay)
        return len(items)
