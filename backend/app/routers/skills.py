import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import github_profile, skillgap
from app.config import settings
from app.database import get_db
from app.normalize import resolve_technology
from app.schemas import SkillGapOut, SkillGapRequest

router = APIRouter(prefix="/skills", tags=["skills"])


def github_client():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "DevIntel-student-project"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    with httpx.Client(headers=headers, timeout=15) as client:
        yield client


@router.post("/gap", response_model=SkillGapOut)
def skill_gap(req: SkillGapRequest, db: Session = Depends(get_db), gh: httpx.Client = Depends(github_client)):
    """Which technologies to learn next, from skills the user picked and/or their public GitHub repos."""
    username = (req.github_username or "").strip().lstrip("@")
    if not req.skills and not username:
        raise HTTPException(422, "Pick at least one skill or enter a GitHub username")
    if len(req.skills) > 40:
        raise HTTPException(422, "Too many skills (maximum 40)")

    known: dict[int, dict] = {}
    unrecognized: list[str] = []
    for name in req.skills:
        tech = resolve_technology(db, name)
        if tech:
            known[tech.id] = {"source": "manual", "repos": None}
        else:
            unrecognized.append(name)

    github_summary = None
    if username:
        try:
            repos = github_profile.fetch_repos(gh, username)
        except github_profile.GithubError as e:
            raise HTTPException(e.status, e.message) from None
        for tech_id, count in github_profile.detect_technologies(db, repos).items():
            was_manual = tech_id in known
            known[tech_id] = {"source": "both" if was_manual else "github", "repos": count}
        github_summary = {"username": username, "repos_scanned": len(repos)}

    result = skillgap.analyze(db, known, category=req.category)
    return SkillGapOut(**result, unrecognized=unrecognized, github=github_summary)
