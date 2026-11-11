from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid, utcnow


class MatchCandidate(Base, TimestampMixin):
    """一对被 blocking 命中并完成加权打分的记录（pair 规范化：left < right）。"""

    __tablename__ = "match_candidates"
    __table_args__ = (
        UniqueConstraint("run_id", "left_record_id", "right_record_id", name="uq_candidate_pair_per_run"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("resolution_runs.id", ondelete="CASCADE"), index=True)
    left_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source_records.id", ondelete="CASCADE"), index=True)
    right_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source_records.id", ondelete="CASCADE"), index=True)

    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    decision: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    blocking_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    features_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(String(400), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
