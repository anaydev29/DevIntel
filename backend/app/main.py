import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import Base, engine, ensure_indexes
from app.routers import auth, compare, discussions, feed, me, meta, moderation, topics, rankings, skills, technologies


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # dev convenience; switch to Alembic migrations later
    try:
        ensure_indexes()
    except Exception as exc:  # an index problem must never stop the site from starting
        print(f"warning: could not create indexes: {exc}")
    yield


app = FastAPI(title="DevIntel API", version="0.1.0",
              description="Developer intelligence and tech trend analysis", lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=800)   # JSON compresses to about a fifth of its size
# Signed, HttpOnly login cookie. Without SESSION_SECRET a random key is used, so logins reset on every restart.
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

# Production frontend (React build) served from the same origin as the API, so no CORS setup is needed.
# During development run `npm run dev` in /frontend instead (it proxies API calls here).
# Mounted last so API routes (/technologies, /rankings, /docs ...) always win.
STATIC_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"  # created by `npm run build`
if STATIC_DIR.exists():
    class FrontendFiles(StaticFiles):
        """Built files in /assets have hashed names, so browsers may keep them for a year; the page itself is always rechecked."""
        async def get_response(self, path, scope):
            response = await super().get_response(path, scope)
            if response.status_code == 200:
                response.headers["Cache-Control"] = ("public, max-age=31536000, immutable" if path.startswith("assets/")
                                                     else "no-cache")
            return response

    app.mount("/", FrontendFiles(directory=STATIC_DIR, html=True), name="frontend")
