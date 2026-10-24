"""Package download collectors: npm and PyPI (public APIs, no key needed).

Only technologies whose main package IS the technology are included (React is the `react` package, Django is
`django`, PyTorch is `torch`). Technologies that only have client libraries on a registry (Redis, MongoDB,
Docker...) are left out on purpose, because their download numbers would measure something else.

These numbers are shown for information (technology popup and Compare). They are NOT part of the DevIntel
Score, because npm and PyPI counts include automated installs and cannot be compared with each other.
Metrics saved: npm.downloads_week / pypi.downloads_week.
"""
import time

import httpx
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, RateLimitError, save_metric
from app.models import Source, Technology

NPM_PACKAGES = {"react": "react", "vue": "vue", "angular": "@angular/core", "svelte": "svelte",
                "nextjs": "next", "typescript": "typescript", "tailwindcss": "tailwindcss"}
PYPI_PACKAGES = {"django": "django", "flask": "flask", "fastapi": "fastapi", "pytorch": "torch",
                 "tensorflow": "tensorflow", "langchain": "langchain"}


class _DownloadsCollector(BaseCollector):
    packages: dict[str, str]
    metric: str

    def __init__(self, client: httpx.Client | None = None, delay: float = 0.5):
        self.client = client or httpx.Client(timeout=20, headers={"User-Agent": "DevIntel-student-project"})
        self.delay = delay

    def _fetch(self, package: str) -> int:
        raise NotImplementedError

    def _get(self, url: str) -> dict:
        resp = self.client.get(url)
        if resp.status_code == 429:
            raise RateLimitError("download stats rate limit")
        resp.raise_for_status()
        return resp.json()

    def process(self, db: Session, source: Source, tech: Technology) -> int:
        package = self.packages.get(tech.slug)
        if package is None:
            return 0                                   # not a technology whose main package is on this registry
        save_metric(db, tech.id, source.id, self.metric, self._fetch(package))
        time.sleep(self.delay)
        return 1


class NpmDownloadsCollector(_DownloadsCollector):
    source_name = "npm"
    packages = NPM_PACKAGES
    metric = "npm.downloads_week"

    def _fetch(self, package: str) -> int:
        return int(self._get(f"https://api.npmjs.org/downloads/point/last-week/{package}")["downloads"])


class PyPIDownloadsCollector(_DownloadsCollector):
    source_name = "pypi"
    packages = PYPI_PACKAGES
    metric = "pypi.downloads_week"

    def _fetch(self, package: str) -> int:
        return int(self._get(f"https://pypistats.org/api/packages/{package}/recent")["data"]["last_week"])
