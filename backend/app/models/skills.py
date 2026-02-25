"""Skill rankings model for placement skill recommendations."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SkillRanking(Base):
    """Cached skill rankings per department."""

    __tablename__ = "skill_rankings"

    department: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Core JSONB data
    summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    skills: Mapped[list] = mapped_column(JSONB, default=list)
    sources: Mapped[list] = mapped_column(JSONB, default=list)
    methodology: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Optional filters that produced this ranking
    filters_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
