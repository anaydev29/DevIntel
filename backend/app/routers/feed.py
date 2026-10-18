from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Article, Technology, TrendingRepo
from app.normalize import resolve_technology
from app.schemas import ArticleOut, RepoOut

router = APIRouter(prefix="/feed", tags=["feed"])


def _article_out(a: Article, tech_slug: str | None) -> ArticleOut:
    return ArticleOut(
        id=a.id, source=a.source, title=a.title, url=a.url,
        discussion_url=f"https://news.ycombinator.com/item?id={a.external_id}" if a.source == "hackernews" else None,
        author=a.author, tags=a.tags or [], published_at=a.published_at, score=a.score,
        comments=a.comments, reading_time=a.reading_time, technology=tech_slug)


@router.get("/blogs", response_model=list[ArticleOut])
def blogs(tech: str | None = None, days: int = Query(14, le=60), limit: int = Query(30, le=100),
          db: Session = Depends(get_db)):
    """Popular recent dev.to articles, optionally for one technology."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (select(Article, Technology.slug).outerjoin(Technology, Technology.id == Article.technology_id)
            .where(Article.source == "devto", Article.published_at >= cutoff))
    if tech:
        t = resolve_technology(db, tech)
        if not t:
            raise HTTPException(404, f"Technology '{tech}' not found")
        stmt = stmt.where(Article.technology_id == t.id)
    rows = db.execute(stmt.order_by(Article.score.desc()).limit(limit)).all()
    return [_article_out(a, slug) for a, slug in rows]


@router.get("/news", response_model=list[ArticleOut])
def news(limit: int = Query(30, le=100), db: Session = Depends(get_db)):
    """Current Hacker News front page (as of the last collection run)."""
    day = db.scalar(select(func.max(Article.fetched_on)).where(Article.source == "hackernews"))
    if day is None:
        return []
    rows = db.scalars(select(Article).where(Article.source == "hackernews", Article.fetched_on == day)
                      .order_by(Article.score.desc()).limit(limit)).all()
    return [_article_out(a, None) for a in rows]


@router.get("/repos", response_model=list[RepoOut])
def repos(language: str | None = None, limit: int = Query(50, le=100), db: Session = Depends(get_db)):
    """Hottest new GitHub repositories (created in the last 7 days), latest snapshot."""
    day: date | None = db.scalar(select(func.max(TrendingRepo.captured_on)))
    if day is None:
        return []
    stmt = select(TrendingRepo).where(TrendingRepo.captured_on == day)
    if language:
        stmt = stmt.where(func.lower(TrendingRepo.language) == language.lower())
    rows = db.scalars(stmt.order_by(TrendingRepo.rank).limit(limit)).all()
    return [RepoOut(rank=r.rank, full_name=r.full_name, url=f"https://github.com/{r.full_name}",
                    description=r.description, language=r.language, stars=r.stars, forks=r.forks,
                    created_at=r.created_at_gh) for r in rows]
