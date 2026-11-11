"""The AI hub: the latest snapshot of trending Hugging Face and Kaggle items."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Technology
from app.models_hub import HubItem

router = APIRouter(prefix="/hub", tags=["hub"])

Source = Literal["huggingface", "kaggle"]
Kind = Literal["model", "dataset", "space", "notebook", "competition"]


class HubItemOut(BaseModel):
    source: str
    kind: str
    rank: int
    title: str
    url: str
    author: str | None
    description: str | None
    tags: list[str]
    downloads: int
    likes: int
    trending_score: float | None
    extra: dict
    technology: str | None      # slug of the matching technology of the catalog, if any
    captured_on: date


class HubSummaryRow(BaseModel):
    source: str
    kind: str
    items: int
    captured_on: date


def _latest(db: Session, source: str | None, kind: str | None):
    query = select(HubItem.source, HubItem.kind, func.max(HubItem.captured_on)).group_by(HubItem.source, HubItem.kind)
    if source:
        query = query.where(HubItem.source == source)
    if kind:
        query = query.where(HubItem.kind == kind)
    return db.execute(query).all()


@router.get("/summary", response_model=list[HubSummaryRow])
def summary(db: Session = Depends(get_db)):
    """Which collections exist, how many items each has, and when it was last collected."""
    out = []
    for source, kind, day in sorted(_latest(db, None, None)):
        count = db.scalar(select(func.count()).select_from(HubItem).where(
            HubItem.source == source, HubItem.kind == kind, HubItem.captured_on == day)) or 0
        out.append(HubSummaryRow(source=source, kind=kind, items=count, captured_on=day))
    return out


@router.get("/items", response_model=list[HubItemOut])
def items(source: Source | None = None, kind: Kind | None = None, limit: int = Query(20, ge=1, le=100),
          db: Session = Depends(get_db)):
    """The newest snapshot of each collection (models, datasets, spaces, notebooks, competitions), in rank order."""
    latest = _latest(db, source, kind)
    if not latest:
        return []
    rows = db.execute(
        select(HubItem, Technology.slug).outerjoin(Technology, Technology.id == HubItem.technology_id)
        .where(or_(*[and_(HubItem.source == s, HubItem.kind == k, HubItem.captured_on == d) for s, k, d in latest]))
        .order_by(HubItem.source, HubItem.kind, HubItem.rank)).all()
    out: list[HubItemOut] = []
    counts: dict[tuple[str, str], int] = {}
    for item, slug in rows:
        key = (item.source, item.kind)
        counts[key] = counts.get(key, 0) + 1
        if counts[key] > limit:
            continue
        out.append(HubItemOut(
            source=item.source, kind=item.kind, rank=item.rank, title=item.title, url=item.url, author=item.author,
            description=item.description, tags=item.tags or [], downloads=item.downloads, likes=item.likes,
            trending_score=item.trending_score, extra=item.extra or {}, technology=slug, captured_on=item.captured_on))
    return out
