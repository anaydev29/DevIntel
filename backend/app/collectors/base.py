"""Shared pipeline logic: run bookkeeping, error handling, snapshot upserts."""
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MetricSnapshot, PipelineRun, Source, Technology


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


class BaseCollector(ABC):
    source_name: str

    @abstractmethod
    def process(self, db: Session, source: Source, tech: Technology) -> int:
        """Fetch and store data for one technology. Return number of records saved."""

    def run(self, db: Session, only_slugs: list[str] | None = None) -> PipelineRun:
        source = get_or_create_source(db, self.source_name)
        run = PipelineRun(source_id=source.id, status="running")
        db.add(run)
        db.commit()

        query = select(Technology).order_by(Technology.slug)
        if only_slugs:
            query = query.where(Technology.slug.in_(only_slugs))
        techs = db.scalars(query).all()

        errors: list[str] = []
        fetched = 0
        for tech in techs:
            try:
                fetched += self.process(db, source, tech)
                db.commit()
            except RateLimitError as e:
                db.rollback()
                errors.append(f"{tech.slug}: rate limited ({e}); run stopped")
                break
            except Exception as e:  # one bad technology must not kill the whole run
                db.rollback()
                errors.append(f"{tech.slug}: {type(e).__name__}: {e}")

        run.records_fetched = fetched
        run.error_count = len(errors)
        run.error_log = "\n".join(errors) or None
        run.status = "success" if not errors else ("partial" if fetched else "failed")
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        return run
