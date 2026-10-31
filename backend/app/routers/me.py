"""Things a signed-in user can save: GitHub username, skills, watchlist. Also account deletion."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.github_profile import USERNAME_RE
from app.models import (Comment, CommentReport, CommentVote, ModerationAction, Thread, TopicMeta, Technology, User, UserBan,
                        UserSkill, WatchlistItem)
from app.normalize import resolve_technology
from app.profile_data import build_profile, skills_of, watchlist_of
from app.routers.auth import require_user
from app.schemas import ProfileOut, ProfileUpdate, SkillsOut, SkillsUpdate, WatchItemOut

router = APIRouter(prefix="/me", tags=["me"])
MAX_SKILLS = 40
MAX_WATCHLIST = 50


@router.get("/profile", response_model=ProfileOut)
def profile(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return build_profile(db, user)


@router.put("/profile", response_model=ProfileOut)
def update_profile(body: ProfileUpdate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    name = (body.github_username or "").strip().lstrip("@")
    if name and not USERNAME_RE.match(name):
        raise HTTPException(422, "That does not look like a valid GitHub username")
    user.github_username = name or None
    db.commit()
    return build_profile(db, user)


@router.put("/skills", response_model=SkillsOut)
def save_skills(body: SkillsUpdate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Replace the saved skill list."""
    if len(body.skills) > MAX_SKILLS:
        raise HTTPException(422, f"Too many skills (maximum {MAX_SKILLS})")
    ids, unrecognized = set(), []
    for name in body.skills:
        tech = resolve_technology(db, name)
        ids.add(tech.id) if tech else unrecognized.append(name)
    db.execute(delete(UserSkill).where(UserSkill.user_id == user.id))
    db.add_all(UserSkill(user_id=user.id, technology_id=i) for i in ids)
    db.commit()
    return SkillsOut(skills=skills_of(db, user), unrecognized=unrecognized)


def _tech_or_404(db: Session, name: str) -> Technology:
    tech = resolve_technology(db, name)
    if not tech:
        raise HTTPException(404, f"Technology '{name}' not found")
    return tech


@router.put("/watchlist/{name}", response_model=list[WatchItemOut])
def watch(name: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    tech = _tech_or_404(db, name)
    exists = db.scalar(select(WatchlistItem).where(WatchlistItem.user_id == user.id, WatchlistItem.technology_id == tech.id))
    if not exists:
        count = db.scalar(select(func.count()).select_from(WatchlistItem).where(WatchlistItem.user_id == user.id))
        if count >= MAX_WATCHLIST:
            raise HTTPException(422, f"Watchlist is full (maximum {MAX_WATCHLIST})")
        db.add(WatchlistItem(user_id=user.id, technology_id=tech.id))
        db.commit()
    return watchlist_of(db, user)


@router.delete("/watchlist/{name}", response_model=list[WatchItemOut])
def unwatch(name: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    tech = _tech_or_404(db, name)
    db.execute(delete(WatchlistItem).where(WatchlistItem.user_id == user.id, WatchlistItem.technology_id == tech.id))
    db.commit()
    return watchlist_of(db, user)


@router.delete("", status_code=204)
def delete_account(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Permanently delete the account and everything saved with it."""
    db.execute(delete(UserSkill).where(UserSkill.user_id == user.id))
    db.execute(delete(WatchlistItem).where(WatchlistItem.user_id == user.id))
    own_ids = list(db.scalars(select(Comment.id).where(Comment.author_id == user.id)))
    reply_ids = list(db.scalars(select(Comment.id).where(Comment.parent_id.in_(own_ids)))) if own_ids else []
    topic_threads = list(db.scalars(select(TopicMeta.thread_id).where(TopicMeta.author_id == user.id)))
    in_topics = list(db.scalars(select(Comment.id).where(Comment.thread_id.in_(topic_threads)))) if topic_threads else []
    gone = list(set(own_ids + reply_ids + in_topics))              # their comments, replies hanging on them, and their topics
    db.execute(delete(CommentVote).where(CommentVote.user_id == user.id))
    db.execute(delete(CommentReport).where(CommentReport.reporter_id == user.id))
    if gone:
        db.execute(delete(CommentVote).where(CommentVote.comment_id.in_(gone)))
        db.execute(delete(CommentReport).where(CommentReport.comment_id.in_(gone)))
        db.execute(delete(Comment).where(Comment.id.in_(gone)))
    if topic_threads:
        db.execute(delete(TopicMeta).where(TopicMeta.thread_id.in_(topic_threads)))
        db.execute(delete(Thread).where(Thread.id.in_(topic_threads)))
    db.execute(delete(UserBan).where(UserBan.user_id == user.id))
    db.execute(update(ModerationAction).where(ModerationAction.moderator_id == user.id).values(moderator_id=None))
    db.delete(user)
    db.commit()
    request.session.clear()
    return Response(status_code=204)
