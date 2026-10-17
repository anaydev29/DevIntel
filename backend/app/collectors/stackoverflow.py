"""Stack Overflow collector (Stack Exchange API v2.3).

Metrics saved daily per technology:
  stackoverflow.total_questions   all-time question count for the tag
  stackoverflow.questions_30d     new questions tagged in the last 30 days
                                  (this is the growth signal; total_questions barely moves)
"""
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import httpx
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, RateLimitError, save_metric
from app.config import settings
from app.models import Source, Technology

API = "https://api.stackexchange.com/2.3"


class StackOverflowCollector(BaseCollector):
    source_name = "stackoverflow"

    def __init__(self, key: str | None = None, client: httpx.Client | None = None, delay: float = 0.3):
        self.key = key or settings.stackexchange_key
        self.client = client or httpx.Client(timeout=20, headers={"User-Agent": "DevIntel-student-project"})
        self.delay = delay

    def _get(self, path: str, params: dict) -> dict:
        params = {"site": "stackoverflow", **params}
        if self.key:
            params["key"] = self.key
        resp = self.client.get(f"{API}{path}", params=params)
        data = resp.json()
        # The API reports throttling inside the JSON body, sometimes with HTTP 400
        if data.get("error_id") == 502 or data.get("quota_remaining") == 0:
            raise RateLimitError(data.get("error_message", "daily quota used up"))
        resp.raise_for_status()
        if data.get("backoff"):  # API asks us to wait this many seconds
            time.sleep(min(int(data["backoff"]), 60))
        return data

    def process(self, db: Session, source: Source, tech: Technology) -> int:
        tag = tech.stackoverflow_tag or tech.slug

        info = self._get(f"/tags/{quote(tag, safe='')}/info", {})
        items = info.get("items", [])
        if not items:
            raise ValueError(f"tag '{tag}' not found on Stack Overflow")
        save_metric(db, tech.id, source.id, "stackoverflow.total_questions", items[0]["count"])

        since = int((datetime.now(timezone.utc) - timedelta(days=30)).timestamp())
        recent = self._get("/questions", {"tagged": tag, "fromdate": since, "filter": "total"})
        save_metric(db, tech.id, source.id, "stackoverflow.questions_30d", recent["total"])

        time.sleep(self.delay)
        return 2
