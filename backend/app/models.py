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


class Article(Base):
    """Blog posts (dev.to) and news stories (Hacker News front page)."""
    __tablename__ = "articles"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_article_source_ext"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20), index=True)  # devto / hackernews
    external_id: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(400))
    url: Mapped[str] = mapped_column(String(800))
    author: Mapped[str | None] = mapped_column(String(120))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    score: Mapped[int] = mapped_column(Integer, default=0)      # dev.to reactions / HN points
    comments: Mapped[int] = mapped_column(Integer, default=0)
    reading_time: Mapped[int | None] = mapped_column(Integer)
    technology_id: Mapped[int | None] = mapped_column(ForeignKey("technologies.id", ondelete="SET NULL"))
    fetched_on: Mapped[date] = mapped_column(Date)              # last day we saw it (HN: on the front page)


class TrendingRepo(Base):
    """Daily snapshot of hot new GitHub repositories (GitHub has no official trending API)."""
    __tablename__ = "trending_repos"
    __table_args__ = (UniqueConstraint("captured_on", "github_id", name="uq_trending_per_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    captured_on: Mapped[date] = mapped_column(Date, index=True)
    rank: Mapped[int] = mapped_column(Integer)
    github_id: Mapped[int] = mapped_column(Integer)
    full_name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(60))
    stars: Mapped[int] = mapped_column(Integer, default=0)
    forks: Mapped[int] = mapped_column(Integer, default=0)
    created_at_gh: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class User(Base):
    """A person who signed in with Google. We store only what we need: id, email, name, avatar."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    google_sub: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(320))
    name: Mapped[str | None] = mapped_column(String(200))
    avatar_url: Mapped[str | None] = mapped_column(String(800))
    github_username: Mapped[str | None] = mapped_column(String(39))
    role: Mapped[str] = mapped_column(String(20), default="user")  # user / moderator / admin (used in Phase 3)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserSkill(Base):
    __tablename__ = "user_skills"
    __table_args__ = (UniqueConstraint("user_id", "technology_id", name="uq_user_skill"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    technology_id: Mapped[int] = mapped_column(ForeignKey("technologies.id", ondelete="CASCADE"))


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (UniqueConstraint("user_id", "technology_id", name="uq_user_watch"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    technology_id: Mapped[int] = mapped_column(ForeignKey("technologies.id", ondelete="CASCADE"))
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Thread(Base):
    """A discussion. Today: one per technology / article / repo. Later: kind="general" user topics (with a title)."""
    __tablename__ = "threads"
    __table_args__ = (UniqueConstraint("kind", "ref", name="uq_thread_target"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), index=True)      # technology / article / repo / general
    ref: Mapped[str] = mapped_column(String(200))                  # tech slug, article id, repo full name
    title: Mapped[str | None] = mapped_column(String(200))         # used by general topics later
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    thread_id: Mapped[int] = mapped_column(ForeignKey("threads.id", ondelete="CASCADE"), index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"))  # one level deep
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    body: Mapped[str] = mapped_column(Text)                        # plain text only
    status: Mapped[str] = mapped_column(String(10), default="visible")   # visible / deleted / hidden
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CommentVote(Base):
    __tablename__ = "comment_votes"
    __table_args__ = (UniqueConstraint("comment_id", "user_id", name="uq_vote"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))


class CommentReport(Base):
    __tablename__ = "comment_reports"
    __table_args__ = (UniqueConstraint("comment_id", "reporter_id", name="uq_report"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    comment_id: Mapped[int] = mapped_column(ForeignKey("comments.id", ondelete="CASCADE"), index=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserBan(Base):
    """A banned user can still read everything but cannot post, vote, edit or report."""
    __tablename__ = "user_bans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    reason: Mapped[str | None] = mapped_column(String(300))
    banned_by: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ModerationAction(Base):
    """Audit log: every restore, removal, ban, unban and role change. Ids are plain integers so the log survives deletions."""
    __tablename__ = "moderation_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    moderator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(20))        # restore / remove / ban / unban / promote / demote
    comment_id: Mapped[int | None] = mapped_column(Integer, index=True)
    target_user_id: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
