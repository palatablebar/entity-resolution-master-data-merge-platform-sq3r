"""SourceRecord 序列化。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.constants.enums import SOURCE_SYSTEM_LABELS


def serialize_record(row: Any, *, include_raw: bool = False) -> dict[str, Any]:
    payload = {
        "id": str(row.id),
        "source_system": row.source_system,
        "source_label": SOURCE_SYSTEM_LABELS.get(row.source_system, row.source_system),
        "external_id": row.external_id,
        "full_name": row.full_name,
        "phone": row.phone,
        "email": row.email,
        "address": row.address,
        "city": row.city,
        "normalized_name": row.normalized_name,
        "normalized_phone": row.normalized_phone,
        "normalized_email": row.normalized_email,
        "normalized_address": row.normalized_address,
        "normalized_city": row.normalized_city,
        "source_updated_at": _iso(row.source_updated_at),
        "created_at": _iso(row.created_at),
    }
    if include_raw:
        payload["raw_payload"] = row.raw_payload
    return payload


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None
