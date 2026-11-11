"""EntityCluster 序列化。"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from src.constants.enums import ClusterStatus


def serialize_cluster(row: Any, *, members: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    payload = {
        "id": str(row.id),
        "run_id": str(row.run_id),
        "cluster_key": row.cluster_key,
        "member_ids": row.member_ids,
        "member_keys": row.member_keys,
        "record_count": row.record_count,
        "confidence": row.confidence,
        "status": row.status,
        "edge_type": row.edge_type,
        "created_at": row.created_at.isoformat() if isinstance(row.created_at, datetime) else row.created_at,
    }
    if members is not None:
        payload["members"] = members
    return payload


def serialize_cluster_member(record: dict[str, Any], reliability_hint: str | None = None) -> dict[str, Any]:
    return {**record, "reliability_hint": reliability_hint}


CLUSTER_STATUS_LABELS = {
    ClusterStatus.AUTO_MERGED.value: "自动合并",
    ClusterStatus.PENDING_REVIEW.value: "待复核",
    ClusterStatus.CONFIRMED.value: "已确认",
}
