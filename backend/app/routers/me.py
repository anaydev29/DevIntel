"""Things a signed-in user can save: GitHub username, skills, watchlist. Also account deletion."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.github_profile import USERNAME_RE
from app.models import TechScore, Technology, User, UserSkill, WatchlistItem
from app.normalize import resolve_technology
from app.routers.auth import require_user, user_out
from app.schemas import ProfileOut, ProfileUpdate, SkillsOut, SkillsUpdate, WatchItemOut

router = APIRouter(prefix="/me", tags=["me"])
MAX_SKILLS = 40
MAX_WATCHLIST = 50


def _watchlist(db: Session, user: User) -> list[WatchItemOut]:
    day = db.scalar(select(func.max(TechScore.computed_on)))
    scores = {s.technology_id: s for s in db.scalars(select(TechScore).where(TechScore.computed_on == day))} if day else {}
    rows = db.execute(select(Technology).join(WatchlistItem, WatchlistItem.technology_id == Technology.id)
                      .where(WatchlistItem.user_id == user.id).order_by(WatchlistItem.added_at.desc())).scalars()
    return [WatchItemOut(slug=t.slug, name=t.name, category=t.category,
                         devintel_score=scores[t.id].devintel_score if t.id in scores else None,
                         growth_30d=scores[t.id].growth_30d if t.id in scores else None,
                         is_emerging=scores[t.id].is_emerging if t.id in scores else False) for t in rows]


def _skills(db: Session, user: User) -> list[str]:
    return list(db.scalars(select(Technology.slug).join(UserSkill, UserSkill.technology_id == Technology.id)
                           .where(UserSkill.user_id == user.id).order_by(Technology.name)))


@router.get("/profile", response_model=ProfileOut)
def profile(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return ProfileOut(user=user_out(user), skills=_skills(db, user), watchlist=_watchlist(db, user))


@router.put("/profile", response_model=ProfileOut)
def update_profile(body: ProfileUpdate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    name = (body.github_username or "").strip().lstrip("@")
    if name and not USERNAME_RE.match(name):
        raise HTTPException(422, "That does not look like a valid GitHub username")
    user.github_username = name or None
    db.commit()
    return ProfileOut(user=user_out(user), skills=_skills(db, user), watchlist=_watchlist(db, user))


@router.put("/skills", response_model=SkillsOut)
def save_skills(body: SkillsUpdate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Replace the saved skill list."""
    if len(body.skills) > MAX_SKILLS:
        raise HTTPException(422, f"Too many skills (maximum {MAX_SKILLS})")
    ids, unrecognized = set(), []
    for name in body.skills:
        tech = resolve_technology(db, name)
        ids.add(tech.id) if tech else unrecognized.append(name)
    db.execute(delete(UserSkill).where(UserSkill.user_id == user.id))
    db.add_all(UserSkill(user_id=user.id, technology_id=i) for i in ids)
    db.commit()
    return SkillsOut(skills=_skills(db, user), unrecognized=unrecognized)


def _tech_or_404(db: Session, name: str) -> Technology:
    tech = resolve_technology(db, name)
    if not tech:
        raise HTTPException(404, f"Technology '{name}' not found")
    return tech


@router.put("/watchlist/{name}", response_model=list[WatchItemOut])
def watch(name: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    tech = _tech_or_404(db, name)
    exists = db.scalar(select(WatchlistItem).where(WatchlistItem.user_id == user.id, WatchlistItem.technology_id == tech.id))
    if not exists:
        count = db.scalar(select(func.count()).select_from(WatchlistItem).where(WatchlistItem.user_id == user.id))
        if count >= MAX_WATCHLIST:
            raise HTTPException(422, f"Watchlist is full (maximum {MAX_WATCHLIST})")
        db.add(WatchlistItem(user_id=user.id, technology_id=tech.id))
        db.commit()
    return _watchlist(db, user)


@router.delete("/watchlist/{name}", response_model=list[WatchItemOut])
def unwatch(name: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    tech = _tech_or_404(db, name)
    db.execute(delete(WatchlistItem).where(WatchlistItem.user_id == user.id, WatchlistItem.technology_id == tech.id))
    db.commit()
    return _watchlist(db, user)


@router.delete("", status_code=204)
def delete_account(request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    """Permanently delete the account and everything saved with it."""
    db.execute(delete(UserSkill).where(UserSkill.user_id == user.id))
    db.execute(delete(WatchlistItem).where(WatchlistItem.user_id == user.id))
    db.delete(user)
    db.commit()
    request.session.clear()
    return Response(status_code=204)
