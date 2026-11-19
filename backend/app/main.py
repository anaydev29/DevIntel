import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from app.routers import hub

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import Base, engine, ensure_indexes, ensure_row_level_security
from app.limiter import limiter  # <--- NEW
from app.routers import auth, compare, discussions, feed, me, meta, moderation, topics, rankings, skills, technologies

# ... [keep your existing lifespan function exactly as it is] ...

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    try:
        ensure_indexes()
    except Exception as exc:
        print(f"warning: could not create indexes: {exc}")
    try:
        ensure_row_level_security()
    except Exception as exc:
        print(f"warning: could not enable row level security: {exc}")
    yield

is_production = os.getenv("ENVIRONMENT") == "production"

app = FastAPI(
    title="DevIntel API", 
    version="0.1.0",
    description="Developer intelligence and tech trend analysis", 
    lifespan=lifespan,
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json"
)

# --- NEW: Rate Limiting Setup ---
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# --------------------------------

app.add_middleware(GZipMiddleware, minimum_size=800)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret or secrets.token_urlsafe(48),
                   https_only=settings.cookie_secure, same_site="lax", max_age=14 * 24 * 3600)

# ... [keep all your app.include_router lines exactly as they are] ...
# ... [keep your STATIC_DIR and FrontendFiles code exactly as it is] ...