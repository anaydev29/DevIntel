"""Resolve messy technology names to one canonical Technology row."""
from sqlalchemy import case, or_, select
from sqlalchemy.orm import Session

from app.models import Technology, TechnologyAlias


def clean(text: str) -> str:
    return text.strip().lower()


def resolve_technology(db: Session, text: str) -> Technology | None:
    """Find a technology by slug or alias in a single query (an exact slug match wins)."""
    key = clean(text)
    return db.scalar(
        select(Technology)
        .outerjoin(TechnologyAlias, TechnologyAlias.technology_id == Technology.id)
        .where(or_(Technology.slug == key, TechnologyAlias.alias == key))
        .order_by(case((Technology.slug == key, 0), else_=1))
        .limit(1))
