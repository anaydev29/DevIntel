"""Builds the signed-in user's profile (skills and watchlist) with as few queries as possible."""
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models import TechScore, Technology, User, UserSkill, WatchlistItem
from app.schemas import ProfileOut, WatchItemOut


def skills_of(db: Session, user: User) -> list[str]:
    return list(db.scalars(select(Technology.slug).join(UserSkill, UserSkill.technology_id == Technology.id)
                           .where(UserSkill.user_id == user.id).order_by(Technology.name)))


def watchlist_of(db: Session, user: User) -> list[WatchItemOut]:
    """One query: the watched technologies joined with their newest score."""
    latest_day = select(func.max(TechScore.computed_on)).scalar_subquery()
    rows = db.execute(
        select(Technology, TechScore)
        .join(WatchlistItem, WatchlistItem.technology_id == Technology.id)
        .outerjoin(TechScore, and_(TechScore.technology_id == Technology.id, TechScore.computed_on == latest_day))
        .where(WatchlistItem.user_id == user.id).order_by(WatchlistItem.added_at.desc())).all()
    return [WatchItemOut(slug=t.slug, name=t.name, category=t.category,
                         devintel_score=s.devintel_score if s else None, growth_30d=s.growth_30d if s else None,
                         is_emerging=s.is_emerging if s else False) for t, s in rows]


def build_profile(db: Session, user: User) -> ProfileOut:
    from app.routers.auth import user_out   # imported here: auth.py also imports this module
    return ProfileOut(user=user_out(user), skills=skills_of(db, user), watchlist=watchlist_of(db, user))
