from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RuleCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    auto_threshold: float = Field(default=0.92, ge=0.5, le=1.0)
    review_threshold: float = Field(default=0.75, ge=0.3, le=0.99)


class RuleUpdateRequest(BaseModel):
    field_weights: dict[str, float] | None = None
    source_reliability: dict[str, float] | None = None
    auto_threshold: float | None = Field(default=None, ge=0.5, le=1.0)
    review_threshold: float | None = Field(default=None, ge=0.3, le=0.99)
    is_active: bool | None = None


def serialize_rule(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "name": row.name,
        "field_weights": row.field_weights,
        "source_reliability": row.source_reliability,
        "auto_threshold": row.auto_threshold,
        "review_threshold": row.review_threshold,
        "normalization": row.normalization,
        "version": row.version,
        "is_active": row.is_active,
        "updated_at": row.updated_at.isoformat() if isinstance(row.updated_at, datetime) else row.updated_at,
        "created_at": row.created_at.isoformat() if isinstance(row.created_at, datetime) else row.created_at,
    }
