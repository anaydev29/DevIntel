"""Discussions: comments, replies (one level), upvotes and reports on technologies, articles and repos.

Safety rules built in: sign-in to write, plain text only, 2000 characters, at most 2 links, 10 comments per hour,
no duplicate posts, public names shortened to "First L.", and a comment hidden automatically after 3 reports."""
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, literal, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Article, Comment, CommentReport, CommentVote, Thread, TrendingRepo, User
from app.normalize import resolve_technology
from app.modlib import counting_reports
from app.routers.auth import current_user, require_active_user, require_user
from app.schemas import (CommentAuthor, CommentEdit, CommentIn, CommentOut, DiscussionOut, ReportIn, VoteIn,
                         VoteOut)

router = APIRouter(prefix="/discussions", tags=["discussions"])

KINDS = {"technology", "article", "repo", "general"}
MAX_BODY = 2000
MAX_LINKS = 2
MAX_PER_HOUR = 10
HIDE_AFTER_REPORTS = 3        # reports from accounts older than a day; moderators can always undo it
PLACEHOLDER = {"deleted": "[deleted]", "hidden": "[hidden while moderators review a report]", "removed": "[removed by a moderator]"}


def public_name(user: User) -> str:
    """Privacy: show 'Anay S.' instead of the full Google name."""
    parts = (user.name or user.email.split("@")[0]).split()
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[-1][0].upper()}."


def canonical_ref(db: Session, kind: str, ref: str) -> str:
    """Validate that the thing being discussed exists, and return its canonical reference."""
    if kind not in KINDS:
        raise HTTPException(422, "Unknown discussion type")
    ref = ref.strip()
    if kind == "technology":
        tech = resolve_technology(db, ref)
        if not tech:
            raise HTTPException(404, "Technology not found")
        return tech.slug
    if kind == "article":
        if not ref.isdigit() or not db.get(Article, int(ref)):
            raise HTTPException(404, "Article not found")
        return ref
    if kind == "general":
        if not db.scalar(select(Thread.id).where(Thread.kind == "general", Thread.ref == ref)):
            raise HTTPException(404, "Topic not found")
        return ref
    if not db.scalar(select(TrendingRepo.id).where(TrendingRepo.full_name == ref).limit(1)):
        raise HTTPException(404, "Repository not found")
    return ref


def enforce_rate_limit(db: Session, me: User) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    recent = db.scalar(select(func.count()).select_from(Comment).where(Comment.author_id == me.id, Comment.created_at >= cutoff))
    if recent >= MAX_PER_HOUR:
        raise HTTPException(429, "You are posting too fast. Please try again later.")


def clean_body(body: str) -> str:
    body = body.strip()
    if not body:
        raise HTTPException(422, "Write something first")
    if len(body) > MAX_BODY:
        raise HTTPException(422, f"Too long (maximum {MAX_BODY} characters)")
    if len(re.findall(r"https?://", body, flags=re.IGNORECASE)) > MAX_LINKS:
        raise HTTPException(422, f"Please include at most {MAX_LINKS} links")
    return body


def _build(db: Session, kind: str, ref: str, me: User | None) -> DiscussionOut:
    """One query returns every comment with its author, its vote count and whether the viewer voted for it."""
    score_col = select(func.count(CommentVote.id)).where(CommentVote.comment_id == Comment.id).correlate(Comment).scalar_subquery()
    voted_col = (select(CommentVote.id).where(CommentVote.comment_id == Comment.id, CommentVote.user_id == me.id).exists()
                 if me else literal(False))
    rows = db.execute(select(Comment, User, score_col, voted_col.label("voted"))
                      .join(User, User.id == Comment.author_id).join(Thread, Thread.id == Comment.thread_id)
                      .where(Thread.kind == kind, Thread.ref == ref).order_by(Comment.created_at)).all()

    def out(c: Comment, author: User, score: int, voted, replies: list[CommentOut]) -> CommentOut:
        shown = c.status == "visible"
        return CommentOut(
            id=c.id, author=CommentAuthor(name=public_name(author), initial=public_name(author)[0].upper()) if shown else None,
            body=c.body if shown else PLACEHOLDER[c.status], status=c.status, created_at=c.created_at,
            edited_at=c.edited_at, score=score or 0, voted=bool(voted),
            mine=bool(me and c.author_id == me.id), replies=replies)

    children: dict[int, list[CommentOut]] = {}
    for c, author, score, voted in rows:
        if c.parent_id and c.status == "visible":
            children.setdefault(c.parent_id, []).append(out(c, author, score, voted, []))
    top = []
    for c, author, score, voted in rows:
        if c.parent_id:
            continue
        replies = children.get(c.id, [])
        if c.status != "visible" and not replies:
            continue                      # removed comments vanish unless they have replies to hang on
        top.append(out(c, author, score, voted, replies))
    total = sum(1 + len(c.replies) for c in top if c.status == "visible") + sum(len(c.replies) for c in top if c.status != "visible")
    return DiscussionOut(kind=kind, ref=ref, total=total, comments=top)


@router.get("", response_model=DiscussionOut)
def get_discussion(kind: str, ref: str, db: Session = Depends(get_db), me: User | None = Depends(current_user)):
    ref = canonical_ref(db, kind, ref)
    return _build(db, kind, ref, me)


@router.get("/counts", response_model=dict[str, int])
def counts(kind: str, refs: str = Query(..., description="comma separated references"), db: Session = Depends(get_db)):
    """Number of visible comments for several items at once (for the 'Discuss (3)' buttons)."""
    if kind not in KINDS:
        raise HTTPException(422, "Unknown discussion type")
    wanted = [r.strip() for r in refs.split(",") if r.strip()][:100]
    rows = db.execute(select(Thread.ref, func.count(Comment.id)).join(Comment, Comment.thread_id == Thread.id)
                      .where(Thread.kind == kind, Thread.ref.in_(wanted), Comment.status == "visible")
                      .group_by(Thread.ref)).all()
    return {ref: n for ref, n in rows}


@router.post("/comments", response_model=DiscussionOut, status_code=201)
def post_comment(body: CommentIn, db: Session = Depends(get_db), me: User = Depends(require_active_user)):
    ref = canonical_ref(db, body.kind, body.ref)
    text = clean_body(body.body)
    enforce_rate_limit(db, me)

    thread = db.scalar(select(Thread).where(Thread.kind == body.kind, Thread.ref == ref))
    if thread is None:
        thread = Thread(kind=body.kind, ref=ref)
        db.add(thread)
        db.flush()
    duplicate = db.scalar(select(Comment.id).where(Comment.thread_id == thread.id, Comment.author_id == me.id, Comment.body == text,
                                                   Comment.created_at >= datetime.now(timezone.utc) - timedelta(minutes=10)))
    if duplicate:
        raise HTTPException(422, "You already posted exactly this")

    parent_id = None
    if body.parent_id is not None:
        parent = db.get(Comment, body.parent_id)
        if not parent or parent.thread_id != thread.id or parent.status != "visible":
            raise HTTPException(404, "The comment you are replying to was not found")
        parent_id = parent.parent_id or parent.id     # replies to replies attach to the top-level comment
    db.add(Comment(thread_id=thread.id, parent_id=parent_id, author_id=me.id, body=text))
    db.commit()
    return _build(db, body.kind, ref, me)


def _own_visible_comment(db: Session, comment_id: int, me: User) -> Comment:
    c = db.get(Comment, comment_id)
    if not c or c.status != "visible":
        raise HTTPException(404, "Comment not found")
    if c.author_id != me.id:
        raise HTTPException(403, "You can only change your own comments")
    return c


def _thread_view(db: Session, c: Comment, me: User) -> DiscussionOut:
    thread = db.get(Thread, c.thread_id)
    return _build(db, thread.kind, thread.ref, me)


@router.put("/comments/{comment_id}", response_model=DiscussionOut)
def edit_comment(comment_id: int, body: CommentEdit, db: Session = Depends(get_db), me: User = Depends(require_active_user)):
    c = _own_visible_comment(db, comment_id, me)
    c.body, c.edited_at = clean_body(body.body), datetime.now(timezone.utc)
    db.commit()
    return _thread_view(db, c, me)


@router.delete("/comments/{comment_id}", response_model=DiscussionOut)
def delete_comment(comment_id: int, db: Session = Depends(get_db), me: User = Depends(require_user)):
    c = _own_visible_comment(db, comment_id, me)
    c.status = "deleted"
    db.commit()
    return _thread_view(db, c, me)


def _visible_or_404(db: Session, comment_id: int) -> Comment:
    c = db.get(Comment, comment_id)
    if not c or c.status != "visible":
        raise HTTPException(404, "Comment not found")
    return c


@router.put("/comments/{comment_id}/vote", response_model=VoteOut)
def vote(comment_id: int, body: VoteIn, db: Session = Depends(get_db), me: User = Depends(require_active_user)):
    c = _visible_or_404(db, comment_id)
    if c.author_id == me.id:
        raise HTTPException(422, "You cannot vote on your own comment")
    existing = db.scalar(select(CommentVote).where(CommentVote.comment_id == c.id, CommentVote.user_id == me.id))
    if body.voted and not existing:
        db.add(CommentVote(comment_id=c.id, user_id=me.id))
    elif not body.voted and existing:
        db.delete(existing)
    db.commit()
    return VoteOut(score=db.scalar(select(func.count()).select_from(CommentVote).where(CommentVote.comment_id == c.id)), voted=body.voted)


@router.post("/comments/{comment_id}/report", status_code=204)
def report(comment_id: int, body: ReportIn, db: Session = Depends(get_db), me: User = Depends(require_active_user)):
    c = _visible_or_404(db, comment_id)
    if c.author_id == me.id:
        raise HTTPException(422, "You cannot report your own comment")
    if not db.scalar(select(CommentReport.id).where(CommentReport.comment_id == c.id, CommentReport.reporter_id == me.id)):
        db.add(CommentReport(comment_id=c.id, reporter_id=me.id, reason=(body.reason.strip() or "other")[:300]))
        db.flush()
        if counting_reports(db, c.id) >= HIDE_AFTER_REPORTS:
            c.status = "hidden"           # held back until a moderator reviews it
        db.commit()
