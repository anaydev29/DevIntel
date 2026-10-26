from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cache import cached
from app.database import get_db
from app.models import ScoreComponent, TechScore, Technology
from app.backtest import HORIZONS, run_backtest
from app.schemas import BacktestOut, BreakdownOut, BreakdownTech, ComponentOut, RankingItem

router = APIRouter(prefix="/rankings", tags=["rankings"])


def _latest_rows(db: Session, category: str | None, emerging_only: bool):
    latest_day = select(func.max(TechScore.computed_on)).scalar_subquery()   # one query, not two
    stmt = (select(TechScore, Technology).join(Technology, Technology.id == TechScore.technology_id)
            .where(TechScore.computed_on == latest_day))
    if category:
        stmt = stmt.where(Technology.category == category)
    if emerging_only:
        stmt = stmt.where(TechScore.is_emerging.is_(True))
    return db.execute(stmt).all()


def _item(score: TechScore, tech: Technology) -> RankingItem:
    return RankingItem(slug=tech.slug, name=tech.name, category=tech.category,
                       devintel_score=score.devintel_score, growth_30d=score.growth_30d,
                       is_emerging=score.is_emerging, computed_on=score.computed_on)


@router.get("/trending", response_model=list[RankingItem])
@cached()
def trending(category: str | None = None, limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    """Technologies ranked by DevIntel Score (current popularity and activity)."""
    rows = sorted(_latest_rows(db, category, False), key=lambda r: r[0].devintel_score or 0, reverse=True)
    return [_item(s, t) for s, t in rows[:limit]]


@router.get("/emerging", response_model=list[RankingItem])
@cached()
def emerging(category: str | None = None, limit: int = Query(20, le=100), db: Session = Depends(get_db)):
    """Technologies flagged as emerging, fastest growth first. Empty until enough history exists."""
    rows = sorted(_latest_rows(db, category, True), key=lambda r: r[0].growth_30d or 0, reverse=True)
    return [_item(s, t) for s, t in rows[:limit]]


@router.get("/breakdown", response_model=BreakdownOut)
@cached()
def breakdown(db: Session = Depends(get_db)):
    """Every technology's score together with the rank it earned on each signal.
    The dashboard uses it to explain a score and to re-rank with the user's own weights."""
    latest_day = select(func.max(TechScore.computed_on)).scalar_subquery()
    rows = db.execute(select(TechScore, Technology).join(Technology, Technology.id == TechScore.technology_id)
                      .where(TechScore.computed_on == latest_day)).all()
    day = rows[0][0].computed_on if rows else None
    comps: dict[int, dict[str, ComponentOut]] = {}
    weights: dict[str, float] = {}
    if day:
        for c in db.scalars(select(ScoreComponent).where(ScoreComponent.computed_on == day)):
            comps.setdefault(c.technology_id, {})[c.metric] = ComponentOut(value=c.value, rank=c.rank)
            weights[c.metric] = c.weight
    techs = [BreakdownTech(slug=t.slug, name=t.name, category=t.category, devintel_score=s.devintel_score,
                           growth_30d=s.growth_30d, is_emerging=s.is_emerging, components=comps.get(t.id, {}))
             for s, t in sorted(rows, key=lambda r: r[0].devintel_score or 0, reverse=True)]
    return BreakdownOut(computed_on=day, weights=weights, technologies=techs)


@router.get("/backtest", response_model=BacktestOut)
@cached()
def backtest(horizon: int = Query(14), db: Session = Depends(get_db)):
    """Did technologies flagged as "taking off" really keep growing? See app/backtest.py for the method."""
    if horizon not in HORIZONS:
        raise HTTPException(422, f"horizon must be one of {HORIZONS}")
    return run_backtest(db, horizon)
