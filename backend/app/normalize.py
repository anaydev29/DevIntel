"""Resolve messy technology names to one canonical Technology row."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Technology, TechnologyAlias


def clean(text: str) -> str:
    return text.strip().lower()


def resolve_technology(db: Session, text: str) -> Technology | None:
    key = clean(text)
    tech = db.scalar(select(Technology).where(Technology.slug == key))
    if tech:
        return tech
    alias = db.scalar(select(TechnologyAlias).where(TechnologyAlias.alias == key))
    return alias.technology if alias else None
