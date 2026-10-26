from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cache import cached
from app.database import get_db
from app.models import Article, MetricSnapshot, Repository, Source, TechScore, Technology
from app.normalize import resolve_technology
from app.schemas import (HistoryOut, LearnArticle, MetricPoint, SeriesPoint, RelatedTech, RepoLite, TechnologyDetail, TechnologyOut,
                         TechnologyPageOut)
from app.skillgap import cooccurrence

router = APIRouter(prefix="/technologies", tags=["technologies"])


@router.get("", response_model=list[TechnologyOut])
@cached()
def list_technologies(q: str | None = None, category: str | None = None,
                      limit: int = Query(50, le=200), offset: int = 0,
                      db: Session = Depends(get_db)):
    stmt = select(Technology).order_by(Technology.name)
    if q:
        stmt = stmt.where(Technology.name.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(Technology.category == category)
    return db.scalars(stmt.limit(limit).offset(offset)).all()


@router.get("/{name}", response_model=TechnologyDetail)
@cached()
def get_technology(name: str, db: Session = Depends(get_db)):
    tech = resolve_technology(db, name)  # accepts slug or alias, e.g. "reactjs"
    if not tech:
        raise HTTPException(404, f"Technology '{name}' not found")
    return _detail(db, tech)


def _detail(db: Session, tech: Technology) -> TechnologyDetail:
    # newest value of each metric from the last 7 days, in one query (sources may be collected on different days)
    latest: dict[str, float] = {}
    for metric, value in db.execute(select(MetricSnapshot.metric, MetricSnapshot.value).where(
            MetricSnapshot.technology_id == tech.id, MetricSnapshot.captured_on >= date.today() - timedelta(days=7)
    ).order_by(MetricSnapshot.captured_on)):
        latest[metric] = value
    score = db.scalar(select(TechScore).where(TechScore.technology_id == tech.id)
                      .order_by(TechScore.computed_on.desc()).limit(1))
    return TechnologyDetail(slug=tech.slug, name=tech.name, category=tech.category,
                            description=tech.description,
                            aliases=sorted(a.alias for a in tech.aliases), latest_metrics=latest,
                            devintel_score=score.devintel_score if score else None,
                            growth_30d=score.growth_30d if score else None,
                            is_emerging=score.is_emerging if score else False)


@router.get("/{name}/metrics", response_model=list[MetricPoint])
@cached()
def get_metrics(name: str, metric: str | None = None, days: int = Query(90, le=730),
                db: Session = Depends(get_db)):
    tech = resolve_technology(db, name)
    if not tech:
        raise HTTPException(404, f"Technology '{name}' not found")
    stmt = (select(MetricSnapshot, Source.name)
            .join(Source, Source.id == MetricSnapshot.source_id)
            .where(MetricSnapshot.technology_id == tech.id,
                   MetricSnapshot.captured_on >= date.today() - timedelta(days=days))
            .order_by(MetricSnapshot.captured_on))
    if metric:
        stmt = stmt.where(MetricSnapshot.metric == metric)
    return [MetricPoint(metric=s.metric, source=src, value=s.value, captured_on=s.captured_on)
            for s, src in db.execute(stmt)]


BEGINNER_TAGS = {"beginners", "tutorial", "learning", "basics", "productivity"}


@router.get("/{name}/page", response_model=TechnologyPageOut)
@cached()
def technology_page(name: str, db: Session = Depends(get_db)):
    """Everything for a technology's own page: details, related technologies, learning resources, popular repos."""
    tech = resolve_technology(db, name)
    if not tech:
        raise HTTPException(404, f"Technology '{name}' not found")

    # related technologies: those that appear in the same recent dev.to articles
    together = cooccurrence(db)[tech.id].most_common(6)
    names = {t.id: t for t in db.scalars(select(Technology).where(Technology.id.in_([i for i, _ in together])))} if together else {}
    related = [RelatedTech(slug=names[i].slug, name=names[i].name, category=names[i].category, together=n)
               for i, n in together if i in names]

    # learning resources: recent popular articles, beginner-friendly ones first
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    posts = db.scalars(select(Article).where(Article.source == "devto", Article.technology_id == tech.id,
                                             Article.published_at >= cutoff)).all()
    posts.sort(key=lambda a: (not (BEGINNER_TAGS & {t.lower() for t in (a.tags or [])}), -a.score))
    articles = [LearnArticle(id=a.id, title=a.title, url=a.url, author=a.author, score=a.score, reading_time=a.reading_time,
                             beginner=bool(BEGINNER_TAGS & {t.lower() for t in (a.tags or [])})) for a in posts[:6]]

    repos = [RepoLite(full_name=r.full_name, url=f"https://github.com/{r.full_name}", stars=r.stars, language=r.language)
             for r in db.scalars(select(Repository).where(Repository.technology_id == tech.id)
                                 .order_by(Repository.stars.desc()).limit(5))]
    return TechnologyPageOut(technology=_detail(db, tech), related=related, articles=articles, repos=repos)


@router.get("/{name}/history", response_model=HistoryOut)
@cached()
def technology_history(name: str, days: int = Query(90, ge=7, le=365), db: Session = Depends(get_db)):
    """Daily DevIntel Score and every raw signal over time, for the trend charts."""
    tech = resolve_technology(db, name)
    if not tech:
        raise HTTPException(404, f"Technology '{name}' not found")
    since = date.today() - timedelta(days=days)
    score = [SeriesPoint(date=s.computed_on, value=s.devintel_score) for s in db.scalars(
        select(TechScore).where(TechScore.technology_id == tech.id, TechScore.computed_on >= since).order_by(TechScore.computed_on))
        if s.devintel_score is not None]
    metrics: dict[str, list[SeriesPoint]] = {}
    for metric, day, value in db.execute(select(MetricSnapshot.metric, MetricSnapshot.captured_on, MetricSnapshot.value).where(
            MetricSnapshot.technology_id == tech.id, MetricSnapshot.captured_on >= since).order_by(MetricSnapshot.captured_on)):
        metrics.setdefault(metric, []).append(SeriesPoint(date=day, value=value))
    return HistoryOut(slug=tech.slug, name=tech.name, score=score, metrics=metrics)
