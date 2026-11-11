from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    action: str = Field(pattern="^(confirm|reject)$")
    note: str = Field(default="", max_length=400)


def serialize_candidate(row: Any, left: Any | None = None, right: Any | None = None) -> dict[str, Any]:
    from datetime import datetime

    from src.schemas.records import serialize_record

    features = row.features_json.get("features", {}) if isinstance(row.features_json, dict) else {}
    payload = {
        "id": str(row.id),
        "run_id": str(row.run_id),
        "left_record_id": str(row.left_record_id),
        "right_record_id": str(row.right_record_id),
        "score": row.score,
        "decision": row.decision,
        "status": row.status,
        "blocking_keys": row.blocking_keys,
        "features": features,
        "available_weight": row.features_json.get("available_weight") if isinstance(row.features_json, dict) else None,
        "thresholds": row.features_json.get("thresholds") if isinstance(row.features_json, dict) else None,
        "reviewed_at": row.reviewed_at.isoformat() if isinstance(row.reviewed_at, datetime) else row.reviewed_at,
        "review_note": row.review_note,
        "created_at": row.created_at.isoformat() if isinstance(row.created_at, datetime) else row.created_at,
    }
    if left is not None:
        payload["left"] = serialize_record(left)
    if right is not None:
        payload["right"] = serialize_record(right)
    return payload
