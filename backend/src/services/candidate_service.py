"""候选对服务：列表、详情、人工复核（确认/拒绝）。

复核落章后调用 regroup_service 按最终确认的候选关系重新成组：
未决记录保持待定，被拒绝关系不会留在同一身份，黄金档案只由已确认成员重建。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import CandidateDecision, CandidateStatus
from src.models.match_candidate import MatchCandidate
from src.models.resolution_run import ResolutionRun
from src.models.source_record import SourceRecord
from src.models.user import User
from src.schemas.candidates import serialize_candidate
from src.services import audit_service, regroup_service
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


def _regroup_brief(regroup: dict[str, Any]) -> dict[str, Any]:
    """审计载荷用的紧凑成组摘要（完整快照随接口返回）。"""

    def brief(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "cluster_id": item["cluster_id"],
                "status": item["status"],
                "member_keys": item["member_keys"],
                "golden_status": item["golden_status"],
            }
            for item in groups
        ]

    return {
        "before": brief(regroup.get("before", [])),
        "after": brief(regroup.get("after", [])),
        "split": brief(regroup.get("split", [])),
        "pending_edge_ids": [edge["id"] for edge in regroup.get("pending_edges", [])],
    }


def _primary_cluster_id(regroup: dict[str, Any]) -> str | None:
    after = regroup.get("after", [])
    for item in after:
        if item["status"] == "confirmed":
            return item["cluster_id"]
    return after[0]["cluster_id"] if after else None


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
    if row.decision != CandidateDecision.REVIEW.value:
        raise AppError(
            codes.CANDIDATE_LOCKED,
            "只有 review 判定（0.75~0.92 分）的候选需要人工复核",
            f"decision={row.decision}",
        )

    expected = (
        CandidateStatus.CONFIRMED.value if action == "confirm" else CandidateStatus.REJECTED.value
    )
    if row.status != CandidateStatus.PENDING.value:
        if row.status != expected:
            raise AppError(
                codes.CANDIDATE_LOCKED,
                "该候选已被复核，不能重复处理",
                f"status={row.status}",
            )
        # 同一判断重复执行：幂等返回当前成组状态，不新增簇或档案
        regroup = regroup_service.current_regroup_state(
            db, row.run_id, str(row.left_record_id), str(row.right_record_id)
        )
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
                "idempotent_replay": True,
                "regroup": _regroup_brief(regroup),
            },
            ip=ip,
            trace_id=trace_id,
        )
        result = get_candidate(db, candidate_id)
        result["cluster_id"] = _primary_cluster_id(regroup)
        result["regroup"] = regroup
        return result

    # 矛盾守卫：拒绝的关系不能留在同一身份，确认也不能把已拒绝的 pair 圈进同一身份
    conflict = regroup_service.judgment_conflict(
        db, row.run_id, str(row.left_record_id), str(row.right_record_id), action
    )
    if conflict is not None:
        raise AppError(codes.CLUSTER_CONFLICT, conflict, f"candidate={row.id} action={action}")

    row.status = expected
    row.reviewed_by = user.id
    row.reviewed_at = datetime.now(timezone.utc)
    row.review_note = note or ""

    run = db.get(ResolutionRun, row.run_id)
    regroup = regroup_service.apply_regroup(
        db,
        run=run,
        seed_left=str(row.left_record_id),
        seed_right=str(row.right_record_id),
        actor_email=user.email,
        note=note or "",
    )
    db.commit()

    cluster_id = _primary_cluster_id(regroup)
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
            "regroup": _regroup_brief(regroup),
        },
        ip=ip,
        trace_id=trace_id,
    )
    result = get_candidate(db, candidate_id)
    result["cluster_id"] = cluster_id
    result["regroup"] = regroup
    return result
