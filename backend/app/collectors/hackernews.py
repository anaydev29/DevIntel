"""Hacker News collector (Algolia HN Search API, no key needed).

Metrics saved daily per technology (last 30 days, stories only, title match):
  hackernews.stories_30d   number of stories whose title mentions the technology
  hackernews.points_30d    total points of the top-100 matching stories (a "buzz" signal)

Ambiguous names ("go", "swift", "next") are searched with a more specific query.
Matching is title-only to cut noise, but some noise remains: spot-check the top results
during analysis.
"""
import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, RateLimitError, save_metric
from app.models import Source, Technology

API = "https://hn.algolia.com/api/v1/search"

# slug -> query used on HN (default is the technology name)
QUERY_OVERRIDES = {
    "go": "golang",
    "cpp": "c++",
    "nodejs": "node.js",
    "nextjs": "next.js",
    "vue": "vue.js",
    "swift": "swift language",
    "java": "java programming",
    "spring-boot": "spring boot",
    "tailwindcss": "tailwind css",
    "r": "R language",
    "julia": "julia language",
    "dart": "dart language",
    "csharp": "C# programming",
    "rails": "ruby on rails",
    "express": "express.js",
    "aws": "aws",
    "gcp": "google cloud",
    "bootstrap": "bootstrap css",
    "zig": "zig language",
    "lua": "lua language",
    "git": "git",
}


class HackerNewsCollector(BaseCollector):
    source_name = "hackernews"

    def __init__(self, client: httpx.Client | None = None, delay: float = 0.3):
        self.client = client or httpx.Client(timeout=20, headers={"User-Agent": "DevIntel-student-project"})
        self.delay = delay

    def process(self, db: Session, source: Source, tech: Technology) -> int:
        query = QUERY_OVERRIDES.get(tech.slug, tech.name)
        since = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
        resp = self.client.get(API, params={
            "query": query,
            "tags": "story",
            "numericFilters": f"created_at_i>{since}",
            "restrictSearchableAttributes": "title",
            "hitsPerPage": 100,
        })
        if resp.status_code == 429:
            raise RateLimitError("Algolia rate limit")
        resp.raise_for_status()
        data = resp.json()

        points = sum((h.get("points") or 0) for h in data.get("hits", []))
        save_metric(db, tech.id, source.id, "hackernews.stories_30d", data.get("nbHits", 0))
        save_metric(db, tech.id, source.id, "hackernews.points_30d", points)

        time.sleep(self.delay)
        return 2
