from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, new_uuid, utcnow


class SourceRecord(Base, TimestampMixin):
    """上游三源导出的会员原始行 + 后端统一规范化结果。

    自然键：source_system + external_id（seed 幂等 upsert 依据）。
    """

    __tablename__ = "source_records"
    __table_args__ = (UniqueConstraint("source_system", "external_id", name="uq_source_record_natural"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    source_system: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    external_id: Mapped[str] = mapped_column(String(80), nullable=False)

    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    full_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address: Mapped[str | None] = mapped_column(String(400), nullable=True)
    city: Mapped[str | None] = mapped_column(String(60), nullable=True)

    normalized_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    normalized_phone: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    normalized_email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    normalized_address: Mapped[str | None] = mapped_column(String(400), nullable=True)
    normalized_city: Mapped[str | None] = mapped_column(String(60), nullable=True)

    source_updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
