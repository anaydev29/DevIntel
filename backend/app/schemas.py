from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TechnologyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    category: str
    description: str | None = None


class TechnologyDetail(TechnologyOut):
    aliases: list[str]
    latest_metrics: dict[str, float]
    devintel_score: float | None = None
    growth_30d: float | None = None
    is_emerging: bool = False


class RankingItem(BaseModel):
    slug: str
    name: str
    category: str
    devintel_score: float | None
    growth_30d: float | None
    is_emerging: bool
    computed_on: date


class MetricPoint(BaseModel):
    metric: str
    source: str
    value: float
    captured_on: date


class PipelineRunOut(BaseModel):
    id: int
    source: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    records_fetched: int
    error_count: int


class ArticleOut(BaseModel):
    id: int
    source: str
    title: str
    url: str
    discussion_url: str | None = None
    author: str | None
    tags: list[str]
    published_at: datetime | None
    score: int
    comments: int
    reading_time: int | None
    technology: str | None = None


class RepoOut(BaseModel):
    rank: int
    full_name: str
    url: str
    description: str | None
    language: str | None
    stars: int
    forks: int
    created_at: datetime | None
