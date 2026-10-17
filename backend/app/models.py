"""Database schema for DevIntel.

Design notes
- `metric_snapshots` is a long-format time series: one row per
  (technology, source, metric, day). New metrics/sources need no schema change.
- Aliases map messy names ("reactjs", "React.js") to one canonical technology.
- `tech_scores` stores computed analysis results so the dashboard reads
  pre-computed rows instead of recalculating on every request.
"""
from datetime import date, datetime, timezone

from sqlalchemy import (JSON, Boolean, Date, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Technology(Base):
    __tablename__ = "technologies"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(40), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    github_topic: Mapped[str | None] = mapped_column(String(80))
    stackoverflow_tag: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    aliases: Mapped[list["TechnologyAlias"]] = relationship(
        back_populates="technology", cascade="all, delete-orphan")


class TechnologyAlias(Base):
    __tablename__ = "technology_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    technology_id: Mapped[int] = mapped_column(ForeignKey("technologies.id", ondelete="CASCADE"))
    alias: Mapped[str] = mapped_column(String(120), unique=True, index=True)  # stored lowercase

    technology: Mapped[Technology] = relationship(back_populates="aliases")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)


class MetricSnapshot(Base):
    __tablename__ = "metric_snapshots"
    __table_args__ = (
        UniqueConstraint("technology_id", "source_id", "metric", "captured_on",
                         name="uq_snapshot_per_day"),
        Index("ix_snapshot_lookup", "technology_id", "metric", "captured_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    technology_id: Mapped[int] = mapped_column(ForeignKey("technologies.id", ondelete="CASCADE"))
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    metric: Mapped[str] = mapped_column(String(60))  # e.g. github.repo_count
    value: Mapped[float] = mapped_column(Float)
    captured_on: Mapped[date] = mapped_column(Date)

    source: Mapped[Source] = relationship()


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(primary_key=True)
    github_id: Mapped[int] = mapped_column(Integer, unique=True)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    technology_id: Mapped[int | None] = mapped_column(ForeignKey("technologies.id", ondelete="SET NULL"))
    language: Mapped[str | None] = mapped_column(String(60))
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    topics: Mapped[list] = mapped_column(JSON, default=list)
    created_at_gh: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[date] = mapped_column(Date)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")  # running/success/partial/failed
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    error_log: Mapped[str | None] = mapped_column(Text)

    source: Mapped[Source] = relationship()


class TechScore(Base):
    """Filled in by the analysis step (growth, DevIntel Score, emerging flag)."""
    __tablename__ = "tech_scores"
    __table_args__ = (UniqueConstraint("technology_id", "computed_on", name="uq_score_per_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    technology_id: Mapped[int] = mapped_column(ForeignKey("technologies.id", ondelete="CASCADE"))
    computed_on: Mapped[date] = mapped_column(Date)
    devintel_score: Mapped[float | None] = mapped_column(Float)
    growth_30d: Mapped[float | None] = mapped_column(Float)
    is_emerging: Mapped[bool] = mapped_column(Boolean, default=False)
