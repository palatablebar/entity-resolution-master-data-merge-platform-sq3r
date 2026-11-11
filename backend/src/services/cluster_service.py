"""簇服务：列表、详情（成员 + 簇内候选边）。"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.entity_cluster import EntityCluster
from src.models.match_candidate import MatchCandidate
from src.models.source_record import SourceRecord
from src.schemas.clusters import serialize_cluster
from src.schemas.records import serialize_record
from src.utils.errors import not_found
from src.utils.pagination import normalize_page


def list_clusters(
    db: Session,
    *,
    run_id: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    safe_page, safe_size = normalize_page(page, page_size)
    query = db.query(EntityCluster)
    if run_id:
        query = query.filter(EntityCluster.run_id == run_id)
    if status:
        query = query.filter(EntityCluster.status == status)
    total = query.with_entities(func.count(EntityCluster.id)).scalar() or 0
    rows = (
        query.order_by(EntityCluster.confidence.desc(), EntityCluster.created_at.asc())
        .offset((safe_page - 1) * safe_size)
        .limit(safe_size)
        .all()
    )
    return {
        "items": [serialize_cluster(row) for row in rows],
        "page": safe_page,
        "page_size": safe_size,
        "total": total,
        "total_pages": max(1, -(-total // safe_size)) if total else 1,
    }


def get_cluster(db: Session, cluster_id: str) -> dict[str, Any]:
    row = db.get(EntityCluster, cluster_id)
    if row is None:
        raise not_found("EntityCluster", cluster_id)
    member_uuids = [uuid.UUID(str(member_id)) for member_id in (row.member_ids or [])]
    records = (
        db.query(SourceRecord).filter(SourceRecord.id.in_(member_uuids)).all() if member_uuids else []
    )
    record_by_id = {str(record.id): record for record in records}
    members = [
        serialize_record(record_by_id[str(member_id)]) for member_id in row.member_ids if str(member_id) in record_by_id
    ]

    edges: list[dict[str, Any]] = []
    if member_uuids:
        edge_rows = (
            db.query(MatchCandidate)
            .filter(
                MatchCandidate.run_id == row.run_id,
                MatchCandidate.left_record_id.in_(member_uuids),
                MatchCandidate.right_record_id.in_(member_uuids),
            )
            .order_by(MatchCandidate.score.desc())
            .all()
        )
        edges = [
            {
                "id": str(edge.id),
                "left_record_id": str(edge.left_record_id),
                "right_record_id": str(edge.right_record_id),
                "score": edge.score,
                "decision": edge.decision,
                "status": edge.status,
            }
            for edge in edge_rows
        ]

    payload = serialize_cluster(row, members=members)
    payload["edges"] = edges
    return payload
