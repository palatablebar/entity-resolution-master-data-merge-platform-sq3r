from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid, utcnow


class EntityCluster(Base, TimestampMixin):
    """并查集连通分量。auto 边自动成簇；review 边只生成待复核簇，不自动连通。"""

    __tablename__ = "entity_clusters"
    __table_args__ = (UniqueConstraint("run_id", "cluster_key", name="uq_cluster_key_per_run"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resolution_runs.id", ondelete="CASCADE"), index=True)
    cluster_key: Mapped[str] = mapped_column(String(120), nullable=False)
    member_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    member_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    edge_type: Mapped[str] = mapped_column(String(20), nullable=False, default="auto")
    review_notes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
