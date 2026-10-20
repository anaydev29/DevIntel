from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.routers import compare, feed, meta, rankings, skills, technologies


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # dev convenience; switch to Alembic migrations later
    yield


app = FastAPI(title="DevIntel API", version="0.1.0",
              description="Developer intelligence and tech trend analysis", lifespan=lifespan)
app.include_router(meta.router)
app.include_router(technologies.router)
app.include_router(rankings.router)
app.include_router(feed.router)
app.include_router(compare.router)
app.include_router(skills.router)

# Production frontend (React build) served from the same origin as the API, so no CORS setup is needed.
# During development run `npm run dev` in /frontend instead (it proxies API calls here).
# Mounted last so API routes (/technologies, /rankings, /docs ...) always win.
STATIC_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"  # created by `npm run build`
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="frontend")
