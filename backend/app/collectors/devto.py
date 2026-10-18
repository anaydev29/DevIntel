"""dev.to collector (official public API, no key needed for reading).

For each technology, fetch the most popular articles of the last 7 days that carry its dev.to tag.
"""
import time
from datetime import date, datetime

import httpx
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, RateLimitError, upsert_article
from app.models import Source, Technology

API = "https://dev.to/api/articles"
# slug -> dev.to tag, where they differ
TAG_OVERRIDES = {"nodejs": "node", "postgresql": "postgres", "spring-boot": "springboot",
                 "vue": "vue", "tailwindcss": "tailwindcss"}


def parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


class DevToCollector(BaseCollector):
    source_name = "devto"

    def __init__(self, client: httpx.Client | None = None, delay: float = 0.5, per_tag: int = 10, days: int = 7):
        self.client = client or httpx.Client(timeout=20, headers={
            "User-Agent": "DevIntel-student-project", "Accept": "application/vnd.forem.api-v1+json"})
        self.delay, self.per_tag, self.days = delay, per_tag, days

    def process(self, db: Session, source: Source, tech: Technology) -> int:
        tag = TAG_OVERRIDES.get(tech.slug, tech.slug)
        resp = self.client.get(API, params={"tag": tag, "top": self.days, "per_page": self.per_tag})
        if resp.status_code == 429:
            raise RateLimitError("dev.to rate limit")
        resp.raise_for_status()
        saved = 0
        for a in resp.json():
            raw_tags = a.get("tag_list") or a.get("tags") or []
            if isinstance(raw_tags, str):
                raw_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
            upsert_article(
                db, "devto", str(a["id"]),
                title=a["title"][:400], url=a.get("url") or a.get("canonical_url"),
                author=(a.get("user") or {}).get("name"), tags=raw_tags,
                published_at=parse_time(a.get("published_timestamp") or a.get("published_at")),
                score=a.get("public_reactions_count") or a.get("positive_reactions_count") or 0,
                comments=a.get("comments_count") or 0, reading_time=a.get("reading_time_minutes"),
                technology_id=tech.id, fetched_on=date.today())
            saved += 1
        time.sleep(self.delay)
        return saved
