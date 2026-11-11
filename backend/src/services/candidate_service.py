"""候选对服务：列表、详情、人工复核（确认/拒绝）。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import CandidateDecision, CandidateStatus, ClusterStatus, GoldenStatus, RunStatus
from src.models.entity_cluster import EntityCluster
from src.models.golden_record import GoldenRecord
from src.models.match_candidate import MatchCandidate
from src.models.source_record import SourceRecord
from src.models.user import User
from src.schemas.candidates import serialize_candidate
from src.schemas.records import serialize_record
from src.services import audit_service
from src.utils.errors import AppError, not_found
from src.utils.pagination import normalize_page


def _record_map(db: Session, candidates: list[MatchCandidate]) -> dict[str, SourceRecord]:
    ids: set[str] = set()
    for row in candidates:
        ids.add(str(row.left_record_id))
        ids.add(str(row.right_record_id))
    if not ids:
        return {}
    rows = db.query(SourceRecord).filter(SourceRecord.id.in_([uuid.UUID(i) for i in ids])).all()
    return {str(row.id): row for row in rows}


def list_candidates(
    db: Session,
    *,
    run_id: str | None,
    decision: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    safe_page, safe_size = normalize_page(page, page_size)
    query = db.query(MatchCandidate)
    if run_id:
        query = query.filter(MatchCandidate.run_id == run_id)
    if decision:
        query = query.filter(MatchCandidate.decision == decision)
    if status:
        query = query.filter(MatchCandidate.status == status)
    total = query.with_entities(func.count(MatchCandidate.id)).scalar() or 0
    rows = (
        query.order_by(MatchCandidate.score.desc(), MatchCandidate.created_at.asc())
        .offset((safe_page - 1) * safe_size)
        .limit(safe_size)
        .all()
    )
    records = _record_map(db, rows)
    items = [
        serialize_candidate(
            row,
            records.get(str(row.left_record_id)),
            records.get(str(row.right_record_id)),
        )
        for row in rows
    ]
    return {
        "items": items,
        "page": safe_page,
        "page_size": safe_size,
        "total": total,
        "total_pages": max(1, -(-total // safe_size)) if total else 1,
    }


def get_candidate(db: Session, candidate_id: str) -> dict[str, Any]:
    row = db.get(MatchCandidate, candidate_id)
    if row is None:
        raise not_found("MatchCandidate", candidate_id)
    left = db.get(SourceRecord, row.left_record_id)
    right = db.get(SourceRecord, row.right_record_id)
    payload = serialize_candidate(row, left, right)
    if left is not None:
        payload["left"]["raw_payload"] = left.raw_payload
    if right is not None:
        payload["right"]["raw_payload"] = right.raw_payload
    return payload


def review_candidate(
    db: Session,
    candidate_id: str,
    *,
    action: str,
    note: str,
    user: User,
    ip: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    row = db.get(MatchCandidate, candidate_id)
    if row is None:
        raise not_found("MatchCandidate", candidate_id)
    if row.status != CandidateStatus.PENDING.value:
        raise AppError(
            codes.CANDIDATE_LOCKED,
            "该候选已被复核，不能重复处理",
            f"status={row.status}",
        )
    if row.decision != CandidateDecision.REVIEW.value:
        raise AppError(
            codes.CANDIDATE_LOCKED,
            "只有 review 判定（0.75~0.92 分）的候选需要人工复核",
            f"decision={row.decision}",
        )

    row.status = CandidateStatus.CONFIRMED.value if action == "confirm" else CandidateStatus.REJECTED.value
    row.reviewed_by = user.id
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_note = note or ""
    db.commit()

    cluster_id: str | None = None
    if action == "confirm":
        cluster = (
            db.query(EntityCluster)
            .filter(
                EntityCluster.run_id == row.run_id,
                EntityCluster.member_ids.contains([str(row.left_record_id), str(row.right_record_id)]),
            )
            .first()
        )
        if cluster is not None:
            cluster_id = str(cluster.id)
            cluster.status = ClusterStatus.CONFIRMED.value
            cluster.review_notes = {
                **(cluster.review_notes or {}),
                "confirmed_by": str(user.id),
                "confirmed_at": datetime.now(timezone.utc).isoformat(),
                "note": note or "",
            }
            golden = db.query(GoldenRecord).filter(GoldenRecord.cluster_id == cluster.id).first()
            if golden is not None:
                golden.status = GoldenStatus.ACTIVE.value
            db.commit()

    audit_service.record(
        db,
        action=f"candidate.{action}",
        entity_type="MatchCandidate",
        entity_id=str(row.id),
        actor_id=str(user.id),
        actor_email=user.email,
        payload={
            "score": row.score,
            "decision": row.decision,
            "note": note,
            "cluster_id": cluster_id,
        },
        ip=ip,
        trace_id=trace_id,
    )
    result = get_candidate(db, candidate_id)
    result["cluster_id"] = cluster_id
    return result
