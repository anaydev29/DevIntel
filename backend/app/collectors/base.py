"""Shared pipeline logic: run bookkeeping, error handling, snapshot upserts."""
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Article, MetricSnapshot, PipelineRun, Source, Technology


def safe_http_url(url: str | None) -> str | None:
    """Only web links may be stored: a 'javascript:' or 'data:' link from an outside source would run code when clicked."""
    url = (url or "").strip()
    return url if url.lower().startswith(("http://", "https://")) and len(url) <= 800 else None


class RateLimitError(Exception):
    """Raised when an API says stop; aborts the run but keeps data already saved."""


def get_or_create_source(db: Session, name: str) -> Source:
    source = db.scalar(select(Source).where(Source.name == name))
    if not source:
        source = Source(name=name)
        db.add(source)
        db.commit()
    return source


def save_metric(db: Session, tech_id: int, source_id: int, metric: str,
                value: float, day: date | None = None) -> None:
    """Insert or update today's value so re-running the job never duplicates rows."""
    day = day or date.today()
    row = db.scalar(select(MetricSnapshot).where(
        MetricSnapshot.technology_id == tech_id, MetricSnapshot.source_id == source_id,
        MetricSnapshot.metric == metric, MetricSnapshot.captured_on == day))
    if row:
        row.value = value
    else:
        db.add(MetricSnapshot(technology_id=tech_id, source_id=source_id,
                              metric=metric, value=value, captured_on=day))


def upsert_article(db: Session, source: str, external_id: str, **fields) -> None:
    """Insert or refresh an article so re-running a collector never duplicates rows."""
    if "url" in fields:
        url = safe_http_url(fields["url"])
        if not url:
            return                                      # no usable web link: skip this item
        fields["url"] = url
    row = db.scalar(select(Article).where(Article.source == source, Article.external_id == external_id))
    if not row:
        row = Article(source=source, external_id=external_id)
        db.add(row)
    for key, value in fields.items():
        setattr(row, key, value)


class BaseCollector(ABC):
    source_name: str
    per_technology = True  # False for collectors that fetch one global feed

    @abstractmethod
    def process(self, db: Session, source: Source, tech: Technology | None) -> int:
        """Fetch and store data (for one technology, or the whole feed). Return records saved."""

    def run(self, db: Session, only_slugs: list[str] | None = None) -> PipelineRun:
        source = get_or_create_source(db, self.source_name)
        run = PipelineRun(source_id=source.id, status="running")
        db.add(run)
        db.commit()

        query = select(Technology).order_by(Technology.slug)
        if only_slugs:
            query = query.where(Technology.slug.in_(only_slugs))
        techs = db.scalars(query).all() if self.per_technology else [None]

        label = lambda t: t.slug if t else self.source_name  # noqa: E731
        errors: list[str] = []
        fetched = 0
        for tech in techs:
            try:
                fetched += self.process(db, source, tech)
                db.commit()
            except RateLimitError as e:
                db.rollback()
                errors.append(f"{label(tech)}: rate limited ({e}); run stopped")
                break
            except Exception as e:  # one bad technology must not kill the whole run
                db.rollback()
                errors.append(f"{label(tech)}: {type(e).__name__}: {e}")

        run.records_fetched = fetched
        run.error_count = len(errors)
        run.error_log = "\n".join(errors) or None
        run.status = "success" if not errors else ("partial" if fetched else "failed")
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return run
