from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.routers import meta, rankings, technologies


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)  # dev convenience; switch to Alembic migrations later
    yield


app = FastAPI(title="DevIntel API", version="0.1.0",
              description="Developer intelligence and tech trend analysis", lifespan=lifespan)
app.include_router(meta.router)
app.include_router(technologies.router)
app.include_router(rankings.router)
