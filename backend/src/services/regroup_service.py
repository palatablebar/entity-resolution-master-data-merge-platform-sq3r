"""人工复核后的重新成组：按最终确认的候选关系重建簇与黄金档案。

每次 confirm/reject 落章后，对受影响作用域（被复核 pair 沿 auto/review 边
连通的全部记录）执行：

  1. 用 algorithms.regroup 的纯函数重算目标分组（确定性、可幂等重放）；
  2. 现有簇成员集合与目标分组一致 → 就地更新状态并重建黄金档案；
     不一致 → 标记 split（已拆分），其黄金档案退役（retired），不下发营销；
  3. 没有对应现有簇的目标分组 → 以确定性 cluster_key 建「人工成组」簇，
     同一判断重复执行只会命中同一行，不新增簇或档案；
  4. 黄金档案只由已确认成员重建：未接受来源不会进入字段来源或落选候选。

返回的 before/after 快照供页面展示处理前后的成员、待定关系与档案状态。
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from src.algorithms.clustering import arbitrate_golden, entity_key_for
from src.algorithms.regroup import (
    GROUP_CONFIRMED,
    ScopeEdge,
    build_regroup_plan,
    check_judgment,
    collect_scope,
)
from src.algorithms.types import RecordView
from src.constants.enums import (
    ClusterStatus,
    GoldenStatus,
)
from src.constants.weights import DEFAULT_FIELD_WEIGHTS, DEFAULT_SOURCE_RELIABILITY
from src.models.entity_cluster import EntityCluster
from src.models.golden_record import GoldenRecord
from src.models.match_candidate import MatchCandidate
from src.models.merge_rule import MergeRule
from src.models.resolution_run import ResolutionRun
from src.models.source_record import SourceRecord
from src.utils.logger import get_logger

logger = get_logger("entresolv.regroup")

EDGE_TYPE_CURATED = "curated"
MAX_EVENTS_KEPT = 20


# ------------------------------------------------------------------ 作用域 ----


def _load_scope_edges(db: Session, run_id: Any) -> list[ScopeEdge]:
    rows = db.query(MatchCandidate).filter(MatchCandidate.run_id == run_id).all()
    return [
        ScopeEdge(
            candidate_id=str(row.id),
            left_id=str(row.left_record_id),
            right_id=str(row.right_record_id),
            score=float(row.score),
            decision=str(row.decision),
            status=str(row.status),
        )
        for row in rows
    ]


def _plan_for(db: Session, run_id: Any, seed_left: str, seed_right: str):
    edges = _load_scope_edges(db, run_id)
    scope = collect_scope(seed_left, seed_right, edges)
    return build_regroup_plan(scope, edges)


def judgment_conflict(db: Session, run_id: Any, left_id: str, right_id: str, action: str) -> str | None:
    """落章前守卫：确认/拒绝与已落定的人工结论矛盾时返回中文原因。"""
    edges = _load_scope_edges(db, run_id)
    scope = collect_scope(left_id, right_id, edges)
    scope_edges = [e for e in edges if e.left_id in scope and e.right_id in scope]
    return check_judgment(action, left_id, right_id, scope_edges)


# ------------------------------------------------------------------ 快照 ----


def _cluster_snapshot(cluster: EntityCluster, golden: GoldenRecord | None) -> dict[str, Any]:
    return {
        "cluster_id": str(cluster.id),
        "cluster_key": cluster.cluster_key,
        "edge_type": cluster.edge_type,
        "status": cluster.status,
        "member_ids": [str(member) for member in (cluster.member_ids or [])],
        "member_keys": list(cluster.member_keys or []),
        "record_count": cluster.record_count,
        "confidence": cluster.confidence,
        "golden_id": str(golden.id) if golden is not None else None,
        "golden_status": golden.status if golden is not None else None,
    }


def _pending_edge_payload(edge: ScopeEdge, member_keys: dict[str, str]) -> dict[str, Any]:
    return {
        "id": edge.candidate_id,
        "left_record_id": edge.left_id,
        "right_record_id": edge.right_id,
        "left_key": member_keys.get(edge.left_id, edge.left_id),
        "right_key": member_keys.get(edge.right_id, edge.right_id),
        "score": edge.score,
        "status": edge.status,
    }


def _curated_key(members: list[str]) -> str:
    """人工成组簇的确定性键：同一成员集合永远命中同一行（幂等）。"""
    digest = hashlib.sha1(f"curated:{'|'.join(sorted(members))}".encode("utf-8")).hexdigest()[:16]
    return digest


# ------------------------------------------------------------------ 落库 ----


def _append_event(cluster: EntityCluster, event: str, actor_email: str, note: str, now: datetime) -> None:
    notes = dict(cluster.review_notes or {})
    events = list(notes.get("events", []))
    events.append(
        {
            "event": event,
            "at": now.isoformat(),
            "actor": actor_email,
            "note": note,
        }
    )
    notes["events"] = events[-MAX_EVENTS_KEPT:]
    cluster.review_notes = notes


def _group_status(kind: str) -> str:
    return ClusterStatus.CONFIRMED.value if kind == GROUP_CONFIRMED else ClusterStatus.PENDING_REVIEW.value


def _golden_status_for(kind: str) -> str:
    return GoldenStatus.ACTIVE.value if kind == GROUP_CONFIRMED else GoldenStatus.PROVISIONAL.value


def _rebuild_golden(
    db: Session,
    *,
    run: ResolutionRun,
    cluster: EntityCluster,
    members: list[str],
    kind: str,
    confidence: float,
    views: dict[str, RecordView],
    source_reliability: dict[str, float],
    field_names: list[str],
    reference_time: datetime,
) -> GoldenRecord:
    """黄金档案只由本分组成员重建：未接受来源不进字段来源或落选候选。"""
    arbitration = arbitrate_golden(
        members=members,
        records_by_id=views,
        source_reliability=source_reliability,
        fields=field_names,
        reference_time=reference_time,
    )
    golden = db.query(GoldenRecord).filter(GoldenRecord.cluster_id == cluster.id).first()
    desired = {
        "entity_key": entity_key_for(members),
        "field_values": arbitration["field_values"],
        "conflict_fields": arbitration["conflict_fields"],
        "confidence": confidence,
        "status": _golden_status_for(kind),
    }
    if golden is None:
        golden = GoldenRecord(run_id=run.id, cluster_id=cluster.id, **desired)
        db.add(golden)
    else:
        for field, value in desired.items():
            setattr(golden, field, value)
    db.flush()
    return golden


def apply_regroup(
    db: Session,
    *,
    run: ResolutionRun,
    seed_left: str,
    seed_right: str,
    actor_email: str,
    note: str = "",
) -> dict[str, Any]:
    """落章后对作用域重新成组并重建黄金档案。调用方负责事务提交。"""
    plan = _plan_for(db, run.id, seed_left, seed_right)
    scope_ids = plan.scope_record_ids
    now = datetime.now(timezone.utc)

    records = (
        db.query(SourceRecord).filter(SourceRecord.id.in_([uuid.UUID(rid) for rid in scope_ids])).all()
        if scope_ids
        else []
    )
    views = {str(row.id): RecordView.from_model(row) for row in records}
    member_keys = {rid: views[rid].display_key() for rid in scope_ids if rid in views}

    rule = db.get(MergeRule, run.rule_id) if run.rule_id else None
    if rule is None:
        rule = (
            db.query(MergeRule)
            .filter(MergeRule.is_active.is_(True))
            .order_by(MergeRule.created_at.asc())
            .first()
        )
    field_names = list(rule.field_weights.keys()) if rule is not None else list(DEFAULT_FIELD_WEIGHTS.keys())
    source_reliability = (
        dict(rule.source_reliability) if rule is not None else dict(DEFAULT_SOURCE_RELIABILITY)
    )
    reference_time = run.started_at or now

    all_clusters = db.query(EntityCluster).filter(EntityCluster.run_id == run.id).all()
    goldens = db.query(GoldenRecord).filter(GoldenRecord.run_id == run.id).all()
    golden_by_cluster = {str(golden.cluster_id): golden for golden in goldens}

    scope_set = set(scope_ids)
    affected = [
        cluster
        for cluster in all_clusters
        if scope_set & {str(member) for member in (cluster.member_ids or [])}
    ]
    before = [
        _cluster_snapshot(cluster, golden_by_cluster.get(str(cluster.id))) for cluster in affected
    ]

    # 1) 现有簇：成员集合与目标分组一致 → 就地更新；否则 → 已拆分 + 档案退役
    remaining = list(plan.groups)
    resolved: list[tuple[Any, EntityCluster]] = []  # (group, cluster)
    split_clusters: list[EntityCluster] = []
    for cluster in affected:
        member_set = sorted(str(member) for member in (cluster.member_ids or []))
        match = next((group for group in remaining if group.members == member_set), None)
        if match is None:
            if cluster.status != ClusterStatus.SPLIT.value:
                cluster.status = ClusterStatus.SPLIT.value
                _append_event(cluster, "split", actor_email, note, now)
            golden = golden_by_cluster.get(str(cluster.id))
            if golden is not None and golden.status != GoldenStatus.RETIRED.value:
                golden.status = GoldenStatus.RETIRED.value
            split_clusters.append(cluster)
            continue
        cluster.status = (
            ClusterStatus.AUTO_MERGED.value
            if cluster.edge_type == "auto" and match.kind == GROUP_CONFIRMED
            else _group_status(match.kind)
        )
        cluster.record_count = len(match.members)
        cluster.member_keys = [member_keys.get(mid, mid) for mid in match.members]
        cluster.confidence = match.confidence
        _append_event(cluster, "regroup_keep", actor_email, note, now)
        resolved.append((match, cluster))
        remaining.remove(match)

    # 2) 没有对应现有簇的目标分组 → 确定性 cluster_key 建/复用人工成组簇
    for group in remaining:
        cluster_key = _curated_key(group.members)
        cluster = next((c for c in all_clusters if c.cluster_key == cluster_key), None)
        if cluster is None:
            cluster = EntityCluster(
                run_id=run.id,
                cluster_key=cluster_key,
                member_ids=list(group.members),
                member_keys=[member_keys.get(mid, mid) for mid in group.members],
                record_count=len(group.members),
                confidence=group.confidence,
                status=_group_status(group.kind),
                edge_type=EDGE_TYPE_CURATED,
                review_notes={},
            )
            db.add(cluster)
            db.flush()
            all_clusters.append(cluster)
            _append_event(cluster, "regroup_create", actor_email, note, now)
        else:
            cluster.status = _group_status(group.kind)
            cluster.record_count = len(group.members)
            cluster.member_keys = [member_keys.get(mid, mid) for mid in group.members]
            cluster.confidence = group.confidence
            _append_event(cluster, "regroup_keep", actor_email, note, now)
        resolved.append((group, cluster))

    # 3) 每个目标分组重建黄金档案（只含本组成员）
    rebuilt_golden: dict[str, GoldenRecord] = {}
    for group, cluster in resolved:
        golden = _rebuild_golden(
            db,
            run=run,
            cluster=cluster,
            members=group.members,
            kind=group.kind,
            confidence=group.confidence,
            views=views,
            source_reliability=source_reliability,
            field_names=field_names,
            reference_time=reference_time,
        )
        rebuilt_golden[str(cluster.id)] = golden

    order = {id(group): index for index, group in enumerate(plan.groups)}
    resolved.sort(key=lambda pair: order[id(pair[0])])
    after = [
        _cluster_snapshot(cluster, rebuilt_golden[str(cluster.id)]) for _, cluster in resolved
    ]
    split = [
        _cluster_snapshot(cluster, golden_by_cluster.get(str(cluster.id)))
        for cluster in split_clusters
    ]
    pending_edges = [_pending_edge_payload(edge, member_keys) for edge in plan.pending_edges]

    logger.info(
        "regroup run=%s scope=%d before=%d after=%d split=%d pending=%d",
        run.id,
        len(scope_ids),
        len(before),
        len(after),
        len(split),
        len(pending_edges),
    )
    return {
        "scope_record_ids": scope_ids,
        "before": before,
        "after": after,
        "split": split,
        "pending_edges": pending_edges,
    }


def current_regroup_state(
    db: Session,
    run_id: Any,
    seed_left: str,
    seed_right: str,
) -> dict[str, Any]:
    """只读快照：同一判断重复执行时返回当前成组状态，不新增簇或档案。"""
    plan = _plan_for(db, run_id, seed_left, seed_right)
    scope_set = set(plan.scope_record_ids)
    records = (
        db.query(SourceRecord)
        .filter(SourceRecord.id.in_([uuid.UUID(rid) for rid in plan.scope_record_ids]))
        .all()
        if plan.scope_record_ids
        else []
    )
    member_keys = {
        str(row.id): RecordView.from_model(row).display_key() for row in records
    }
    clusters = db.query(EntityCluster).filter(EntityCluster.run_id == run_id).all()
    goldens = db.query(GoldenRecord).filter(GoldenRecord.run_id == run_id).all()
    golden_by_cluster = {str(golden.cluster_id): golden for golden in goldens}
    current = [
        _cluster_snapshot(cluster, golden_by_cluster.get(str(cluster.id)))
        for cluster in clusters
        if cluster.status != ClusterStatus.SPLIT.value
        and scope_set & {str(member) for member in (cluster.member_ids or [])}
    ]
    current.sort(key=lambda item: (item["status"] != "confirmed", item["member_ids"]))
    return {
        "scope_record_ids": plan.scope_record_ids,
        "before": [],
        "after": current,
        "split": [],
        "pending_edges": [
            _pending_edge_payload(edge, member_keys) for edge in plan.pending_edges
        ],
        "idempotent": True,
    }
