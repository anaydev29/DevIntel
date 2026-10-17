from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import MetricSnapshot, Source, Technology
from app.normalize import resolve_technology
from app.schemas import MetricPoint, TechnologyDetail, TechnologyOut

router = APIRouter(prefix="/technologies", tags=["technologies"])


@router.get("", response_model=list[TechnologyOut])
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
def get_technology(name: str, db: Session = Depends(get_db)):
    tech = resolve_technology(db, name)  # accepts slug or alias, e.g. "reactjs"
    if not tech:
        raise HTTPException(404, f"Technology '{name}' not found")

    latest_day = db.scalar(select(func.max(MetricSnapshot.captured_on))
                           .where(MetricSnapshot.technology_id == tech.id))
    latest: dict[str, float] = {}
    if latest_day:
        rows = db.execute(select(MetricSnapshot.metric, MetricSnapshot.value).where(
            MetricSnapshot.technology_id == tech.id, MetricSnapshot.captured_on == latest_day))
        latest = {m: v for m, v in rows}
    return TechnologyDetail(slug=tech.slug, name=tech.name, category=tech.category,
                            description=tech.description,
                            aliases=sorted(a.alias for a in tech.aliases), latest_metrics=latest)


@router.get("/{name}/metrics", response_model=list[MetricPoint])
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
