"""Test setup.

By default every test uses its own in-memory SQLite database. Set TEST_DATABASE_URL to a PostgreSQL URL to run
the same tests against real PostgreSQL (what production uses): each test then gets its own empty schema."""
import atexit
import os
import uuid

import pytest
import sqlalchemy

from app.config import settings

settings.cache_seconds = 0  # tests must see fresh data; the cache has its own tests that switch it on

PG_URL = os.environ.get("TEST_DATABASE_URL")
_engines: list = []
if PG_URL:
    _real_create_engine = sqlalchemy.create_engine
    _schemas: list[str] = []

    def _create_engine(url, *args, **kwargs):
        if str(url) != "sqlite://":
            return _real_create_engine(url, *args, **kwargs)
        schema = "t_" + uuid.uuid4().hex[:12]
        admin = _real_create_engine(PG_URL)
        with admin.begin() as conn:
            conn.execute(sqlalchemy.text(f'CREATE SCHEMA "{schema}"'))
        admin.dispose()
        _schemas.append(schema)
        engine = _real_create_engine(PG_URL, connect_args={"options": f"-csearch_path={schema}"}, pool_size=1, max_overflow=0)
        _engines.append(engine)
        return engine

    sqlalchemy.create_engine = _create_engine

    @atexit.register
    def _cleanup():
        for engine in _engines:                        # close pooled connections politely first
            engine.dispose()
        admin = _real_create_engine(PG_URL)
        for schema in _schemas:                        # one transaction per schema: dropping them all at once runs out of lock slots
            try:
                with admin.begin() as conn:
                    conn.execute(sqlalchemy.text("SET LOCAL lock_timeout = '2s'"))
                    conn.execute(sqlalchemy.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
            except Exception:                          # a test left a session open: end other connections and retry once
                with admin.begin() as conn:
                    conn.execute(sqlalchemy.text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                                                 "WHERE datname = current_database() AND pid <> pg_backend_pid()"))
                with admin.begin() as conn:
                    conn.execute(sqlalchemy.text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin.dispose()


@pytest.fixture(autouse=True)
def _close_postgres_connections_after_each_test():
    """Each test makes its own engine; PostgreSQL allows only about 100 connections, so close them as we go."""
    start = len(_engines) if PG_URL else 0
    yield
    if PG_URL:
        for engine in _engines[start:]:
            engine.dispose()
