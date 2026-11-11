"""Shared pieces of the Hugging Face and Kaggle collectors."""
from datetime import date

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector, RateLimitError
from app.models import PipelineRun, Technology
from app.models_hub import HubItem
from app.normalize import resolve_technology

USER_AGENT = "DevIntel-student-project"


def clip(text: str | None, limit: int) -> str | None:
    if not text:
        return None
    flat = " ".join(str(text).split())
    return flat if len(flat) <= limit else flat[: limit - 1].rstrip() + "\u2026"


def to_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def check_status(resp: httpx.Response, what: str) -> None:
    if resp.status_code == 429:
        raise RateLimitError(f"{what}: too many requests")
    resp.raise_for_status()


class TechLinker:
    """Maps a tag such as "pytorch" to a technology of the catalog (cached for the run)."""

    def __init__(self, db: Session):
        self.db = db
        self.cache: dict[str, int | None] = {}

    def link(self, tags: list[str]) -> int | None:
        for tag in tags:
            key = str(tag).lower()
            if key not in self.cache:
                tech = resolve_technology(self.db, key)
                self.cache[key] = tech.id if tech else None
            if self.cache[key]:
                return self.cache[key]
        return None


def upsert_hub_item(db: Session, source: str, kind: str, external_id: str, day: date, **fields) -> None:
    """Insert or refresh today's row so re-running a collector never duplicates it."""
    row = db.scalar(select(HubItem).where(HubItem.source == source, HubItem.kind == kind,
                                          HubItem.external_id == external_id, HubItem.captured_on == day))
    if not row:
        row = HubItem(source=source, kind=kind, external_id=external_id, captured_on=day)
        db.add(row)
    for key, value in fields.items():
        setattr(row, key, value)


class SectionsCollector(BaseCollector):
    """A collector for one global feed made of several sections (for example models, datasets, spaces).

    Each section is fetched on its own: if one fails, the others are still saved and the run is
    marked "partial" with the error in its log. If every section fails the run is marked "failed".
    """
    per_technology = False

    def __init__(self, client: httpx.Client | None = None, delay: float | None = None):
        self.client = client or httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT})
        self.delay = 0.5 if delay is None else delay
        self._errors: list[str] = []

    def sections(self) -> list[tuple[str, callable]]:
        """[(label, function(db, source, day) -> records saved)]"""
        raise NotImplementedError

    def process(self, db: Session, source, tech: Technology | None) -> int:
        day = date.today()
        saved = 0
        failures: list[str] = []
        for label, fetch in self.sections():
            try:
                saved += fetch(db, source, day)
                db.commit()
            except RateLimitError as e:
                db.rollback()
                failures.append(f"{label}: rate limited ({e})")
                break
            except Exception as e:  # one failing section must not stop the others
                db.rollback()
                failures.append(f"{label}: {type(e).__name__}: {e}")
        if failures and not saved:
            raise ValueError("; ".join(failures))
        self._errors = failures
        return saved

    def run(self, db: Session, only_slugs: list[str] | None = None) -> PipelineRun:
        self._errors = []
        run = super().run(db, only_slugs)
        if self._errors:
            run.error_count += len(self._errors)
            run.error_log = "\n".join(filter(None, [run.error_log, *self._errors]))
            if run.status == "success":
                run.status = "partial"
            db.commit()
        return run
