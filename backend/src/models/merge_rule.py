from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid, utcnow


class MergeRule(Base, TimestampMixin):
    """规则集：字段权重 + 阈值 + 来源可靠性 + 规范化策略。自然键 name。"""

    __tablename__ = "merge_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    field_weights: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False, default=dict)
    source_reliability: Mapped[dict[str, float]] = mapped_column(JSONB, nullable=False, default=dict)
    auto_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.92)
    review_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.75)
    normalization: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
