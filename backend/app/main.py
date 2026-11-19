import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import Base, engine, ensure_indexes, ensure_row_level_security
from app.limiter import limiter
from app.routers import auth, compare, discussions, feed, me, meta, moderation, topics, rankings, skills, technologies, hub


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

# Rate limiting setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(GZipMiddleware, minimum_size=800)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret or secrets.token_urlsafe(48),
                   https_only=settings.cookie_secure, same_site="lax", max_age=14 * 24 * 3600)

app.include_router(meta.router)
app.include_router(technologies.router)
app.include_router(rankings.router)
app.include_router(feed.router)
app.include_router(compare.router)
app.include_router(skills.router)
app.include_router(auth.router)
app.include_router(me.router)
app.include_router(discussions.router)
app.include_router(moderation.router)
app.include_router(topics.router)
app.include_router(hub.router)


# --- BULLETPROOF STATIC DIR RESOLUTION ---
# __file__ is /app/backend/app/main.py
# .parent is /app/backend/app
# .parent is /app/backend
# .parent is /app (the repo root)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = REPO_ROOT / "frontend" / "dist"

# -----------------------------------------

if STATIC_DIR.exists():
    class FrontendFiles(StaticFiles):
        """Built files in /assets have hashed names, so browsers may keep them for a year; the page itself is always rechecked."""
        async def get_response(self, path, scope):
            response = await super().get_response(path, scope)
            if response.status_code == 200:
                normalized = path.replace("\\", "/")
                response.headers["Cache-Control"] = ("public, max-age=31536000, immutable" if normalized.startswith("assets/")
                                                     else "no-cache")
            return response

    app.mount("/", FrontendFiles(directory=STATIC_DIR, html=True), name="frontend")
else:
    print("--- DEVINTEL WARNING: Frontend dist not found! Serving API only. ---")