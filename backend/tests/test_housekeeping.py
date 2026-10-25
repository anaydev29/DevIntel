from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, ensure_row_level_security, rls_statements
from app.list_users import fetch_users
from app.models import UserBan
from app.routers.auth import upsert_google_user


def test_rls_statements_cover_every_table_and_are_quoted():
    statements = rls_statements(Base.metadata.tables)
    assert len(statements) == len(Base.metadata.tables) >= 20
    assert 'ALTER TABLE "users" ENABLE ROW LEVEL SECURITY' in statements and 'ALTER TABLE "comments" ENABLE ROW LEVEL SECURITY' in statements
    assert all(s.startswith('ALTER TABLE "') for s in statements)


def test_rls_is_skipped_on_sqlite():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    ensure_row_level_security(engine)          # would fail on SQLite if it ran: it must be a quiet no-op


def test_list_users_shows_role_and_ban_status():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    a = upsert_google_user(db, {"sub": "g1", "email": "a@example.com", "name": "Ana"})
    b = upsert_google_user(db, {"sub": "g2", "email": "b@example.com", "name": "Bo"})
    db.add(UserBan(user_id=b.id)); db.commit()
    rows = {u["email"]: u for u in fetch_users(db)}
    assert set(rows) == {"a@example.com", "b@example.com"}
    assert rows["b@example.com"]["banned"] is True and rows["a@example.com"]["banned"] is False
    assert rows["a@example.com"]["role"] == "user"
