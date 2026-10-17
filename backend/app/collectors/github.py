"""GitHub collector: per technology, search repos by topic.

Metrics saved daily (so growth can be computed later):
  github.repo_count   total public repos tagged with the topic
  github.top_stars    stars summed over the top-10 repos for that topic
  github.top_forks    forks summed over the top-10 repos
"""
import time
from datetime import date, datetime

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, RateLimitError, save_metric
from app.config import settings
from app.models import Repository, Source, Technology

API = "https://api.github.com/search/repositories"


class GitHubCollector(BaseCollector):
    source_name = "github"

    def __init__(self, token: str | None = None):
        token = token or settings.github_token
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "DevIntel-student-project"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client = httpx.Client(headers=headers, timeout=20)
        # Search API limits: 30 req/min with token, 10 req/min without
        self.delay = 2.2 if token else 6.5

    def process(self, db: Session, source: Source, tech: Technology) -> int:
        topic = tech.github_topic or tech.slug
        resp = self.client.get(API, params={"q": f"topic:{topic}", "sort": "stars",
                                            "order": "desc", "per_page": 10})
        if resp.status_code in (403, 429) and resp.headers.get("x-ratelimit-remaining") == "0":
            raise RateLimitError(f"resets at {resp.headers.get('x-ratelimit-reset')}")
        resp.raise_for_status()
        data = resp.json()
        items = data.get("items", [])

        save_metric(db, tech.id, source.id, "github.repo_count", data.get("total_count", 0))
        save_metric(db, tech.id, source.id, "github.top_stars", sum(i["stargazers_count"] for i in items))
        save_metric(db, tech.id, source.id, "github.top_forks", sum(i["forks_count"] for i in items))

        for i in items:
            repo = db.scalar(select(Repository).where(Repository.github_id == i["id"]))
            if not repo:
                repo = Repository(github_id=i["id"], full_name=i["full_name"])
                db.add(repo)
            repo.technology_id = tech.id
            repo.language = i.get("language")
            repo.stars = i["stargazers_count"]
            repo.forks = i["forks_count"]
            repo.topics = i.get("topics", [])
            repo.created_at_gh = datetime.fromisoformat(i["created_at"].replace("Z", "+00:00"))
            repo.last_seen = date.today()

        time.sleep(self.delay)
        return 3 + len(items)
