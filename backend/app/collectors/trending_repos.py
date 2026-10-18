"""Trending repositories: GitHub has no official trending API, so we find the most-starred
repositories CREATED in the last 7 days (overall and for the main languages) and snapshot them daily."""
import time
from datetime import date, datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, RateLimitError
from app.config import settings
from app.models import Source, Technology, TrendingRepo

API = "https://api.github.com/search/repositories"
LANGUAGES = ["python", "javascript", "typescript", "go", "rust", "java", "c++"]


class TrendingReposCollector(BaseCollector):
    source_name = "github_trending"
    per_technology = False

    def __init__(self, token: str | None = None, client: httpx.Client | None = None, delay: float | None = None):
        token = token or settings.github_token
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "DevIntel-student-project"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client = client or httpx.Client(headers=headers, timeout=20)
        self.delay = delay if delay is not None else (2.2 if token else 6.5)

    def process(self, db: Session, source: Source, tech: Technology | None) -> int:
        since = (date.today() - timedelta(days=7)).isoformat()
        queries = [(f"created:>={since}", 30)] + [(f"created:>={since} language:{lang}", 20) for lang in LANGUAGES]
        repos: dict[int, dict] = {}
        for q, n in queries:
            resp = self.client.get(API, params={"q": q, "sort": "stars", "order": "desc", "per_page": n})
            if resp.status_code in (403, 429) and resp.headers.get("x-ratelimit-remaining") == "0":
                raise RateLimitError(f"resets at {resp.headers.get('x-ratelimit-reset')}")
            resp.raise_for_status()
            for item in resp.json().get("items", []):
                repos[item["id"]] = item
            time.sleep(self.delay)

        today = date.today()
        ranked = sorted(repos.values(), key=lambda r: r["stargazers_count"], reverse=True)
        for rank, r in enumerate(ranked, 1):
            row = db.scalar(select(TrendingRepo).where(TrendingRepo.captured_on == today,
                                                       TrendingRepo.github_id == r["id"]))
            if not row:
                row = TrendingRepo(captured_on=today, github_id=r["id"])
                db.add(row)
            row.rank, row.full_name = rank, r["full_name"]
            row.description = (r.get("description") or "")[:500] or None
            row.language, row.stars, row.forks = r.get("language"), r["stargazers_count"], r["forks_count"]
            row.created_at_gh = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        return len(ranked)
