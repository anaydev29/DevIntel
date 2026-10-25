"""Free topics: any signed-in user can start a discussion, optionally about a technology or an article on DevIntel.
A topic is a Thread of kind "general"; its opening post is the first comment, so replies, votes, reports,
moderation, bans and rate limits all work exactly as they do for comments."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Article, Comment, Technology, Thread, TopicMeta, User
from app.normalize import resolve_technology
from app.routers.auth import require_active_user
from app.routers.discussions import clean_body, enforce_rate_limit, public_name
from app.schemas import CommentAuthor, TopicArticle, TopicIn, TopicOut, TopicTech

router = APIRouter(prefix="/topics", tags=["topics"])
MAX_TOPICS_PER_DAY = 5
TITLE_MIN, TITLE_MAX = 5, 120


def _topic_query():
    """One query for everything a topic card needs. A topic is listed only while its opening post is visible,
    so deleting or removing that post takes the whole topic down."""
    first_id = select(func.min(Comment.id)).where(Comment.thread_id == Thread.id).correlate(Thread).scalar_subquery()
    visible = Comment.status == "visible"
    replies = select(func.count(Comment.id)).where(Comment.thread_id == Thread.id, visible).correlate(Thread).scalar_subquery()
    last = select(func.max(Comment.created_at)).where(Comment.thread_id == Thread.id, visible).correlate(Thread).scalar_subquery()
    stmt = (select(Thread, User, Comment, Technology, Article, replies.label("n"), last.label("last"))
            .join(TopicMeta, TopicMeta.thread_id == Thread.id).join(User, User.id == TopicMeta.author_id)
            .join(Comment, Comment.id == first_id)
            .outerjoin(Technology, Technology.id == TopicMeta.technology_id)
            .outerjoin(Article, Article.id == TopicMeta.article_id)
            .where(Thread.kind == "general", Comment.status == "visible"))
    return stmt, last


def _out(row) -> TopicOut:
    thread, author, first, tech, article, n, last = row
    name = public_name(author)
    return TopicOut(
        ref=thread.ref, title=thread.title or "", author=CommentAuthor(name=name, initial=name[0].upper()),
        created_at=thread.created_at, last_activity=last or thread.created_at, replies=max((n or 1) - 1, 0),
        preview=first.body[:160], first_comment_id=first.id,
        technology=TopicTech(slug=tech.slug, name=tech.name) if tech else None,
        article=TopicArticle(id=article.id, title=article.title, url=article.url) if article else None)


@router.get("", response_model=list[TopicOut])
def list_topics(tech: str | None = None, sort: str = Query("active", pattern="^(active|new)$"),
                limit: int = Query(30, le=100), offset: int = 0, db: Session = Depends(get_db)):
    stmt, last = _topic_query()
    if tech:
        t = resolve_technology(db, tech)
        if not t:
            raise HTTPException(404, f"Technology '{tech}' not found")
        stmt = stmt.where(TopicMeta.technology_id == t.id)
    stmt = stmt.order_by(Thread.created_at.desc() if sort == "new" else last.desc()).limit(limit).offset(offset)
    return [_out(r) for r in db.execute(stmt).all()]


@router.get("/{ref}", response_model=TopicOut)
def get_topic(ref: str, db: Session = Depends(get_db)):
    stmt, _ = _topic_query()
    row = db.execute(stmt.where(Thread.ref == ref)).first()
    if row is None:
        raise HTTPException(404, "Topic not found")
    return _out(row)


@router.post("", response_model=TopicOut, status_code=201)
def create_topic(body: TopicIn, db: Session = Depends(get_db), me: User = Depends(require_active_user)):
    title = " ".join(body.title.split())
    if not TITLE_MIN <= len(title) <= TITLE_MAX:
        raise HTTPException(422, f"The title needs {TITLE_MIN} to {TITLE_MAX} characters")
    if "http://" in title.lower() or "https://" in title.lower():
        raise HTTPException(422, "Please keep links out of the title")
    text = clean_body(body.body)
    enforce_rate_limit(db, me)
    day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    started = db.scalar(select(func.count()).select_from(TopicMeta).where(TopicMeta.author_id == me.id, TopicMeta.created_at >= day_ago))
    if started >= MAX_TOPICS_PER_DAY:
        raise HTTPException(429, f"You can start {MAX_TOPICS_PER_DAY} topics per day. Try again tomorrow.")
    if db.scalar(select(Thread.id).join(TopicMeta, TopicMeta.thread_id == Thread.id)
                 .where(TopicMeta.author_id == me.id, Thread.title == title, TopicMeta.created_at >= day_ago)):
        raise HTTPException(422, "You already started a topic with this title")

    tech = None
    if body.technology:
        tech = resolve_technology(db, body.technology)
        if not tech:
            raise HTTPException(404, "Technology not found")
    if body.article_id is not None and not db.get(Article, body.article_id):
        raise HTTPException(404, "Article not found")

    thread = Thread(kind="general", ref=secrets.token_urlsafe(6), title=title)
    db.add(thread)
    db.flush()
    db.add(TopicMeta(thread_id=thread.id, author_id=me.id, technology_id=tech.id if tech else None, article_id=body.article_id))
    db.add(Comment(thread_id=thread.id, author_id=me.id, body=text))
    db.commit()
    stmt, _ = _topic_query()
    return _out(db.execute(stmt.where(Thread.ref == thread.ref)).first())
