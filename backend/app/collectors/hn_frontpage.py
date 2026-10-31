"""Hacker News front page collector: the news feed (Algolia HN API, no key needed)."""
from datetime import date, datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, RateLimitError, safe_http_url, upsert_article
from app.models import Source, Technology

API = "https://hn.algolia.com/api/v1/search"


class HackerNewsFrontPageCollector(BaseCollector):
    source_name = "hn_frontpage"
    per_technology = False

    def __init__(self, client: httpx.Client | None = None):
        self.client = client or httpx.Client(timeout=20, headers={"User-Agent": "DevIntel-student-project"})

    def process(self, db: Session, source: Source, tech: Technology | None) -> int:
        resp = self.client.get(API, params={"tags": "front_page", "hitsPerPage": 30})
        if resp.status_code == 429:
            raise RateLimitError("Algolia rate limit")
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
        for h in hits:
            oid = h["objectID"]
            upsert_article(
                db, "hackernews", oid,
                title=(h.get("title") or "")[:400],
                url=safe_http_url(h.get("url")) or f"https://news.ycombinator.com/item?id={oid}",
                author=h.get("author"), tags=[],
                published_at=datetime.fromtimestamp(h["created_at_i"], tz=timezone.utc),
                score=h.get("points") or 0, comments=h.get("num_comments") or 0,
                fetched_on=date.today())
        return len(hits)
