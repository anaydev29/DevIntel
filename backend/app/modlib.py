"""Shared moderation helpers (used by discussions and the moderation API)."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CommentReport, ModerationAction, User

RESOLVING = ("restore", "remove")      # actions that close the open reports on a comment
MIN_REPORTER_AGE = timedelta(days=1)   # reports from brand-new accounts do not count towards auto-hide


def last_resolution(db: Session, comment_id: int):
    return db.scalar(select(func.max(ModerationAction.created_at)).where(
        ModerationAction.comment_id == comment_id, ModerationAction.action.in_(RESOLVING)))


def unresolved_reports(db: Session, comment_id: int) -> list[CommentReport]:
    """Reports made after the last moderator decision on this comment."""
    last = last_resolution(db, comment_id)
    rows = db.scalars(select(CommentReport).where(CommentReport.comment_id == comment_id).order_by(CommentReport.created_at)).all()
    return [r for r in rows if last is None or r.created_at > last]


def counting_reports(db: Session, comment_id: int) -> int:
    """Unresolved reports from accounts older than a day (what triggers the automatic hide)."""
    last = last_resolution(db, comment_id)
    cutoff = datetime.now(timezone.utc) - MIN_REPORTER_AGE
    q = (select(func.count()).select_from(CommentReport).join(User, User.id == CommentReport.reporter_id)
         .where(CommentReport.comment_id == comment_id, User.created_at <= cutoff))
    if last is not None:
        q = q.where(CommentReport.created_at > last)
    return db.scalar(q)


def log_action(db: Session, moderator: User, action: str, comment_id: int | None = None,
               target_user_id: int | None = None, note: str | None = None) -> None:
    db.add(ModerationAction(moderator_id=moderator.id, action=action, comment_id=comment_id,
                            target_user_id=target_user_id, note=(note or "")[:300] or None))
