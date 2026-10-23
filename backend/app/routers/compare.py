from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import cached
from app.database import get_db
from app.models import MetricSnapshot, TechScore
from app.normalize import resolve_technology
from app.schemas import CompareOut, CompareTech, ScorePoint

router = APIRouter(tags=["compare"])


@router.get("/compare", response_model=CompareOut)
@cached()
def compare(techs: str = Query(..., description="2 or 3 technologies, comma separated, e.g. fastapi,django"),
            db: Session = Depends(get_db)):
    """Side-by-side data for 2-3 technologies (names or aliases accepted)."""
    names = [n.strip() for n in techs.split(",") if n.strip()]
    if not 2 <= len(names) <= 3:
        raise HTTPException(422, "Give 2 or 3 technologies separated by commas")
    resolved = []
    for name in names:
        tech = resolve_technology(db, name)
        if not tech:
            raise HTTPException(404, f"Technology '{name}' not found")
        resolved.append(tech)
    if len({t.id for t in resolved}) != len(resolved):
        raise HTTPException(422, "Pick different technologies to compare")

    today = date.today()
    ids = [t.id for t in resolved]
    # two queries for all technologies together, instead of two per technology
    metrics: dict[int, dict[str, float]] = {i: {} for i in ids}
    for tid, metric, value in db.execute(select(MetricSnapshot.technology_id, MetricSnapshot.metric, MetricSnapshot.value).where(
            MetricSnapshot.technology_id.in_(ids), MetricSnapshot.captured_on >= today - timedelta(days=7)
    ).order_by(MetricSnapshot.captured_on)):
        metrics[tid][metric] = value
    history: dict[int, list[TechScore]] = {i: [] for i in ids}
    for s_row in db.scalars(select(TechScore).where(
            TechScore.technology_id.in_(ids), TechScore.computed_on >= today - timedelta(days=90)
    ).order_by(TechScore.computed_on)):
        history[s_row.technology_id].append(s_row)

    result = []
    for t in resolved:
        scores = history[t.id]
        latest = scores[-1] if scores else None
        result.append(CompareTech(
            slug=t.slug, name=t.name, category=t.category,
            devintel_score=latest.devintel_score if latest else None,
            growth_30d=latest.growth_30d if latest else None,
            is_emerging=latest.is_emerging if latest else False,
            metrics=metrics[t.id],
            history=[ScorePoint(date=x.computed_on, score=x.devintel_score) for x in scores if x.devintel_score is not None]))
    return CompareOut(technologies=result)
