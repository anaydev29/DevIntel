from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_tech_scores_computed_on ON tech_scores (computed_on)",
    "CREATE INDEX IF NOT EXISTS ix_metric_snapshots_captured_on ON metric_snapshots (captured_on)",
]


def ensure_indexes(bind=None) -> None:
    """Safe to run on every start: adds indexes that older databases do not have yet."""
    with (bind or engine).begin() as conn:
        for statement in INDEXES:
            conn.execute(text(statement))
