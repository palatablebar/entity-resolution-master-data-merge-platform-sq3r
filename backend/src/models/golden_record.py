from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid, utcnow


class GoldenRecord(Base, TimestampMixin):
    """字段级仲裁后的主数据：每个字段带来源引用与 reliability 理由。"""

    __tablename__ = "golden_records"
    __table_args__ = (UniqueConstraint("run_id", "cluster_id", name="uq_golden_per_cluster"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resolution_runs.id", ondelete="CASCADE"), index=True)
    cluster_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entity_clusters.id", ondelete="CASCADE"), index=True)
    entity_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    field_values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    conflict_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
