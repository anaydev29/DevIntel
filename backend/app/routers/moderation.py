"""Moderation tools: review reported comments, ban users, appoint moderators, and an audit log.
Moderators (and admins) see the queue; only admins can appoint or remove moderators."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Comment, CommentReport, ModerationAction, Thread, User, UserBan
from app.modlib import RESOLVING, log_action
from app.routers.auth import require_admin, require_moderator
from app.routers.discussions import public_name
from app.schemas import AdminUserOut, BanIn, CaseOut, LogOut, ModActionIn, ReportInfo, RoleIn

router = APIRouter(prefix="/moderation", tags=["moderation"])


@router.get("/queue", response_model=list[CaseOut])
def queue(db: Session = Depends(get_db), mod: User = Depends(require_moderator)):
    """Comments with open reports, auto-hidden ones first, then the most reported.
    Five queries in total, however many cases there are (each query is a round trip to the database)."""
    reports = db.scalars(select(CommentReport).order_by(CommentReport.created_at)).all()
    ids = {r.comment_id for r in reports}
    if not ids:
        return []
    last_decision = dict(db.execute(select(ModerationAction.comment_id, func.max(ModerationAction.created_at)).where(
        ModerationAction.comment_id.in_(ids), ModerationAction.action.in_(RESOLVING)).group_by(ModerationAction.comment_id)).all())
    comments = {c.id: (c, t, a) for c, t, a in db.execute(select(Comment, Thread, User).join(Thread, Thread.id == Comment.thread_id)
                                                          .join(User, User.id == Comment.author_id).where(Comment.id.in_(ids)))}
    reporters = {u.id: u for u in db.scalars(select(User).where(User.id.in_({r.reporter_id for r in reports})))}
    banned = set(db.scalars(select(UserBan.user_id).where(UserBan.user_id.in_({a.id for _, _, a in comments.values()}))))

    open_reports: dict[int, list[CommentReport]] = {}
    for r in reports:
        last = last_decision.get(r.comment_id)
        if last is None or r.created_at > last:          # only reports made after the last moderator decision
            open_reports.setdefault(r.comment_id, []).append(r)
    cases = []
    for comment_id, rs in open_reports.items():
        c, thread, author = comments[comment_id]
        if c.status == "deleted":
            continue
        cases.append(CaseOut(
            comment_id=c.id, thread_kind=thread.kind, thread_ref=thread.ref, body=c.body, status=c.status,
            created_at=c.created_at, author_id=author.id, author_name=public_name(author), author_banned=author.id in banned,
            reports=[ReportInfo(reason=r.reason, reporter=public_name(reporters[r.reporter_id]), created_at=r.created_at) for r in rs]))
    cases.sort(key=lambda x: (x.status != "hidden", -len(x.reports)))
    return cases


@router.post("/comments/{comment_id}/action", status_code=204)
def comment_action(comment_id: int, body: ModActionIn, db: Session = Depends(get_db), mod: User = Depends(require_moderator)):
    """restore = keep it (show it again if it was hidden); remove = take it down for good. Both close the open reports."""
    if body.action not in ("restore", "remove"):
        raise HTTPException(422, "Action must be 'restore' or 'remove'")
    c = db.get(Comment, comment_id)
    if c is None or c.status == "deleted":
        raise HTTPException(404, "Comment not found")
    c.status = "visible" if body.action == "restore" else "removed"
    log_action(db, mod, body.action, comment_id=c.id, note=body.note)
    db.commit()


def _target(db: Session, user_id: int, actor: User) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    if target.id == actor.id:
        raise HTTPException(422, "You cannot do this to yourself")
    if target.role == "admin" or (target.role == "moderator" and actor.role != "admin"):
        raise HTTPException(403, "You do not have permission to do this to that user")
    return target


@router.post("/users/{user_id}/ban", status_code=204)
def ban(user_id: int, body: BanIn, db: Session = Depends(get_db), mod: User = Depends(require_moderator)):
    target = _target(db, user_id, mod)
    if not db.scalar(select(UserBan.id).where(UserBan.user_id == target.id)):
        db.add(UserBan(user_id=target.id, reason=(body.reason or "")[:300] or None, banned_by=mod.id))
        log_action(db, mod, "ban", target_user_id=target.id, note=body.reason)
        db.commit()


@router.delete("/users/{user_id}/ban", status_code=204)
def unban(user_id: int, db: Session = Depends(get_db), mod: User = Depends(require_moderator)):
    target = _target(db, user_id, mod)
    existing = db.scalar(select(UserBan).where(UserBan.user_id == target.id))
    if existing:
        db.delete(existing)
        log_action(db, mod, "unban", target_user_id=target.id)
        db.commit()


@router.get("/log", response_model=list[LogOut])
def log(limit: int = Query(50, le=200), db: Session = Depends(get_db), mod: User = Depends(require_moderator)):
    rows = db.scalars(select(ModerationAction).order_by(ModerationAction.created_at.desc(), ModerationAction.id.desc()).limit(limit)).all()
    names = {u.id: public_name(u) for u in db.scalars(select(User).where(User.id.in_({r.moderator_id for r in rows if r.moderator_id})))}
    return [LogOut(id=r.id, moderator=names.get(r.moderator_id, "Deleted user"), action=r.action, comment_id=r.comment_id,
                   target_user_id=r.target_user_id, note=r.note, created_at=r.created_at) for r in rows]


@router.get("/users", response_model=list[AdminUserOut])
def users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    banned = set(db.scalars(select(UserBan.user_id)))
    return [AdminUserOut(id=u.id, name=u.name or "", email=u.email, role=u.role, banned=u.id in banned, created_at=u.created_at)
            for u in db.scalars(select(User).order_by(User.created_at.desc()).limit(200))]


@router.put("/users/{user_id}/role", status_code=204)
def set_role(user_id: int, body: RoleIn, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if body.role not in ("moderator", "user"):
        raise HTTPException(422, "Role must be 'moderator' or 'user'")
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    if target.id == admin.id or target.role == "admin":
        raise HTTPException(403, "Admins are set in the server settings (ADMIN_EMAILS)")
    if target.role != body.role:
        target.role = body.role
        log_action(db, admin, "promote" if body.role == "moderator" else "demote", target_user_id=target.id)
        db.commit()
