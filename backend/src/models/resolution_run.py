from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid, utcnow


class ResolutionRun(Base, TimestampMixin):
    """一次实体解析运行：blocking → 打分 → 聚类 → golden record。

    params_json 快照当时阈值/权重，保证改规则后历史运行仍可解释。
    """

    __tablename__ = "resolution_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("merge_rules.id", ondelete="SET NULL"), nullable=True)
    run_label: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="queued", index=True)
    params_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    blocking_keys: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    records_scanned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_pairs_raw: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pruned_pairs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    candidate_pairs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    auto_pairs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    review_pairs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_pairs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clusters_auto: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clusters_review: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    golden_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    distribution: Mapped[list[int]] = mapped_column(JSONB, nullable=False, default=list)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    triggered_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
