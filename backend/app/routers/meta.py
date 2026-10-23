from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cache import cached
from app.database import get_db
from app.models import PipelineRun, Technology
from app.schemas import PipelineRunOut

router = APIRouter(tags=["meta"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/categories", response_model=list[str])
@cached()
def categories(db: Session = Depends(get_db)):
    return list(db.scalars(select(Technology.category).distinct().order_by(Technology.category)))


@router.get("/pipeline/runs", response_model=list[PipelineRunOut])
@cached()
def pipeline_runs(limit: int = 20, db: Session = Depends(get_db)):
    """Data-freshness log: shows when each source was last collected and how it went."""
    runs = db.scalars(select(PipelineRun).order_by(PipelineRun.started_at.desc()).limit(limit)).all()
    return [PipelineRunOut(id=r.id, source=r.source.name, started_at=r.started_at,
                           finished_at=r.finished_at, status=r.status,
                           records_fetched=r.records_fetched, error_count=r.error_count)
            for r in runs]
