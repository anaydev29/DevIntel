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


def rls_statements(tables) -> list[str]:
    return [f'ALTER TABLE "{name}" ENABLE ROW LEVEL SECURITY' for name in sorted(tables)]


def ensure_row_level_security(bind=None) -> None:
    """Supabase publishes the public schema through a REST API, and a table without Row Level Security can be read
    by anyone holding the project's (public) anon key. Turning RLS on with no policies closes that door.
    This app connects as the table owner, which is not subject to RLS, so nothing changes for it.
    Only runs on PostgreSQL and is safe to repeat; it also covers tables added later."""
    bind = bind or engine
    if bind.dialect.name != "postgresql":
        return
    with bind.begin() as conn:
        for statement in rls_statements(Base.metadata.tables):
            conn.execute(text(statement))
