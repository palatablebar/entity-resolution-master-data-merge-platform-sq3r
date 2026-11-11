"""GoldenRecord 序列化。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.constants.enums import FIELD_LABELS


def serialize_golden(row: Any, *, cluster: Any | None = None) -> dict[str, Any]:
    field_values = row.field_values or {}
    fields = []
    for field, detail in field_values.items():
        fields.append(
            {
                "field": field,
                "label": FIELD_LABELS.get(field, field),
                "value": detail.get("value"),
                "source_system": detail.get("source_system"),
                "source_record_id": detail.get("source_record_id"),
                "source_external_id": detail.get("source_external_id"),
                "reliability": detail.get("reliability", 0.0),
                "reason": detail.get("reason", ""),
                "alternatives": detail.get("alternatives", []),
                "conflict": field in (row.conflict_fields or []),
            }
        )
    payload = {
        "id": str(row.id),
        "run_id": str(row.run_id),
        "cluster_id": str(row.cluster_id),
        "entity_key": row.entity_key,
        "field_values": field_values,
        "fields": fields,
        "conflict_fields": row.conflict_fields or [],
        "confidence": row.confidence,
        "status": row.status,
        "created_at": row.created_at.isoformat() if isinstance(row.created_at, datetime) else row.created_at,
    }
    if cluster is not None:
        payload["cluster"] = {
            "id": str(cluster.id),
            "cluster_key": cluster.cluster_key,
            "record_count": cluster.record_count,
            "confidence": cluster.confidence,
            "status": cluster.status,
            "member_keys": cluster.member_keys,
        }
    return payload
