"""ResolutionRun 序列化。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RunCreateRequest(BaseModel):
    rule_id: str | None = None
    run_label: str = Field(default="", max_length=160)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def serialize_run(row: Any) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "rule_id": str(row.rule_id) if row.rule_id else None,
        "run_label": row.run_label,
        "status": row.status,
        "params": row.params_json,
        "blocking_keys": row.blocking_keys,
        "records_scanned": row.records_scanned,
        "blocked_pairs_raw": row.blocked_pairs_raw,
        "pruned_pairs": row.pruned_pairs,
        "candidate_pairs": row.candidate_pairs,
        "auto_pairs": row.auto_pairs,
        "review_pairs": row.review_pairs,
        "rejected_pairs": row.rejected_pairs,
        "clusters_auto": row.clusters_auto,
        "clusters_review": row.clusters_review,
        "golden_records": row.golden_records,
        "duration_ms": row.duration_ms,
        "distribution": row.distribution,
        "error_message": row.error_message,
        "error_code": row.error_code,
        "started_at": _iso(row.started_at),
        "finished_at": _iso(row.finished_at),
        "created_at": _iso(row.created_at),
    }
