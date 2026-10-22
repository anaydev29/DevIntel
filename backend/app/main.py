import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import auth, compare, discussions, feed, me, meta, rankings, skills, technologies


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # dev convenience; switch to Alembic migrations later
    yield


app = FastAPI(title="DevIntel API", version="0.1.0",
              description="Developer intelligence and tech trend analysis", lifespan=lifespan)
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

# Production frontend (React build) served from the same origin as the API, so no CORS setup is needed.
# During development run `npm run dev` in /frontend instead (it proxies API calls here).
# Mounted last so API routes (/technologies, /rankings, /docs ...) always win.
STATIC_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"  # created by `npm run build`
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
