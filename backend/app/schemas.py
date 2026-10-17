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
