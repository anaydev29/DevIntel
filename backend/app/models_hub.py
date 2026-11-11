"""Table for the AI hub: trending models, datasets, spaces, notebooks and competitions.

The table is created automatically when the API starts (Base.metadata.create_all in main.py)
and when run_pipeline.py runs, as long as this module has been imported.
"""
from datetime import date

from sqlalchemy import JSON, Date, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HubItem(Base):
    """One entry of a daily snapshot from Hugging Face or Kaggle, in rank order."""
    __tablename__ = "hub_items"
    __table_args__ = (
        UniqueConstraint("source", "kind", "external_id", "captured_on", name="uq_hub_item_day"),
        Index("ix_hub_latest", "source", "kind", "captured_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20))            # huggingface / kaggle
    kind: Mapped[str] = mapped_column(String(20))              # model / dataset / space / notebook / competition
    external_id: Mapped[str] = mapped_column(String(300))
    captured_on: Mapped[date] = mapped_column(Date)
    rank: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[str] = mapped_column(String(800))
    author: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(400))
    tags: Mapped[list] = mapped_column(JSON, default=list)
    downloads: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)     # Hugging Face likes, Kaggle votes
    trending_score: Mapped[float | None] = mapped_column(Float)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)    # kind-specific details (reward, deadline, task ...)
    technology_id: Mapped[int | None] = mapped_column(ForeignKey("technologies.id", ondelete="SET NULL"))
