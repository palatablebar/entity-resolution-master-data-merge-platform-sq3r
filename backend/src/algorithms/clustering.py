"""算法 2：并查集聚类 + golden record 字段级 reliability 仲裁。

聚类：
  - 只把 auto 边做并查集连通（review 边不自动连通，交给数据管家复核）
  - review 边在「未被 auto 簇覆盖」的记录上再求连通分量，得到待复核簇
  - 簇置信度 = 簇内最小边分（最弱一环），确定性且保守

golden record 仲裁：
  每个字段对簇内所有有值来源计算
    reliability = 来源权重 × 字段完整度 × 时间衰减
    时间衰减 = 0.5 ** (age_days / 30)，age 以运行快照时刻为基准
  取 reliability 最高者为该字段值，记录来源、数值理由与落选候选；
  同一字段出现多个不同取值 → 记入 conflict_fields 并写审计。
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from src.algorithms.types import RecordView
from src.constants.weights import TIME_DECAY_HALF_LIFE_DAYS


class DisjointSet:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}
        self.rank: dict[str, int] = {}

    def find(self, node: str) -> str:
        if node not in self.parent:
            self.parent[node] = node
            self.rank[node] = 0
            return node
        root = node
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[node] != root:
            self.parent[node], node = root, self.parent[node]
        return root

    def union(self, left: str, right: str) -> None:
        root_left, root_right = self.find(left), self.find(right)
        if root_left == root_right:
            return
        if self.rank[root_left] < self.rank[root_right]:
            root_left, root_right = root_right, root_left
        self.parent[root_right] = root_left
        if self.rank[root_left] == self.rank[root_right]:
            self.rank[root_left] += 1

    def components(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = {}
        for node in self.parent:
            groups.setdefault(self.find(node), []).append(node)
        return groups


def components_from_edges(
    edges: list[tuple[str, str]], excluded: set[str] | None = None
) -> list[list[str]]:
    excluded = excluded or set()
    dsu = DisjointSet()
    for left, right in edges:
        if left in excluded or right in excluded:
            continue
        dsu.union(left, right)
    result: list[list[str]] = []
    for members in dsu.components().values():
        if len(members) >= 2:
            result.append(sorted(members))
    result.sort(key=lambda members: members[0])
    return result


def cluster_confidence(members: list[str], edge_scores: dict[tuple[str, str], float]) -> float:
    scores = []
    member_set = set(members)
    for (left, right), score in edge_scores.items():
        if left in member_set and right in member_set:
            scores.append(score)
    if not scores:
        return 0.0
    return round(min(scores), 4)


def _edge_key(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left < right else (right, left)


def build_clusters(
    auto_edges: list[tuple[str, str]],
    review_edges: list[tuple[str, str]],
    edge_scores: dict[tuple[str, str], float],
) -> dict[str, list[dict[str, Any]]]:
    auto_components = components_from_edges(auto_edges)
    auto_members: set[str] = set()
    for members in auto_components:
        auto_members.update(members)

    review_components = components_from_edges(review_edges, excluded=auto_members)

    def decorate(members: list[str], edge_type: str) -> dict[str, Any]:
        payload_members = members
        key_source = "|".join(members)
        cluster_key = hashlib.sha1(f"{edge_type}:{key_source}".encode("utf-8")).hexdigest()[:16]
        return {
            "cluster_key": cluster_key,
            "members": payload_members,
            "confidence": cluster_confidence(payload_members, edge_scores),
            "edge_type": edge_type,
            "status": "auto_merged" if edge_type == "auto" else "pending_review",
        }

    return {
        "auto": [decorate(members, "auto") for members in auto_components],
        "review": [decorate(members, "review") for members in review_components],
    }


FIELD_DISPLAY: dict[str, str] = {
    "name": "full_name",
    "phone": "phone",
    "email": "email",
    "address": "address",
}


def _decay_factor(source_updated_at: datetime | None, reference_time: datetime) -> float:
    if source_updated_at is None:
        return 1.0
    aware_reference = reference_time
    if source_updated_at.tzinfo is None:
        aware_reference = reference_time.replace(tzinfo=None)
    age_days = max(0.0, (aware_reference - source_updated_at).total_seconds() / 86400.0)
    return 0.5 ** (age_days / TIME_DECAY_HALF_LIFE_DAYS)


def _field_value(field: str, record: RecordView) -> str | None:
    if field == "name":
        return record.full_name
    if field == "phone":
        return record.phone
    if field == "email":
        return record.email
    if field == "address":
        return record.address
    return None


def _normalized_value(field: str, record: RecordView) -> str | None:
    if field == "name":
        return record.normalized_name
    if field == "phone":
        return record.normalized_phone
    if field == "email":
        return record.normalized_email
    if field == "address":
        return record.normalized_address
    return None


def arbitrate_golden(
    members: list[str],
    records_by_id: dict[str, RecordView],
    source_reliability: dict[str, float],
    fields: list[str],
    reference_time: datetime,
) -> dict[str, Any]:
    """对簇内每个字段做 reliability 仲裁，返回 field_values / conflicts / 平均置信度输入。"""
    field_values: dict[str, Any] = {}
    conflict_fields: list[str] = []

    for field in fields:
        candidates: list[dict[str, Any]] = []
        for record_id in members:
            record = records_by_id[record_id]
            value = _field_value(field, record)
            if value is None or str(value).strip() == "":
                continue
            source_weight = float(source_reliability.get(record.source_system, 0.5))
            completeness = 1.0
            decay = _decay_factor(record.source_updated_at, reference_time)
            reliability = round(source_weight * completeness * decay, 4)
            candidates.append(
                {
                    "record": record,
                    "value": value,
                    "normalized": _normalized_value(field, record),
                    "reliability": reliability,
                    "source_weight": source_weight,
                    "decay": round(decay, 4),
                }
            )

        if not candidates:
            field_values[field] = {
                "value": None,
                "source_system": None,
                "source_record_id": None,
                "source_external_id": None,
                "reliability": 0.0,
                "reason": "簇内所有来源该字段为空",
                "alternatives": [],
            }
            continue

        def rank_key(item: dict[str, Any]) -> tuple[float, float, str]:
            updated = item["record"].source_updated_at
            timestamp = updated.timestamp() if updated is not None else 0.0
            return (item["reliability"], timestamp, item["record"].source_system)

        candidates.sort(key=rank_key, reverse=True)
        winner = candidates[0]

        distinct = {candidate["normalized"] for candidate in candidates}
        if len(distinct) > 1:
            conflict_fields.append(field)

        alternatives = [
            {
                "value": candidate["value"],
                "source_system": candidate["record"].source_system,
                "source_external_id": candidate["record"].external_id,
                "reliability": candidate["reliability"],
            }
            for candidate in candidates[1:]
        ]

        field_values[field] = {
            "value": winner["value"],
            "source_system": winner["record"].source_system,
            "source_record_id": winner["record"].id,
            "source_external_id": winner["record"].external_id,
            "reliability": winner["reliability"],
            "reason": (
                f"{winner['record'].source_system} 源权重 {winner['source_weight']:.2f}"
                f" × 完整度 1.00 × 时间衰减 {winner['decay']:.2f}"
                f" = {winner['reliability']:.2f}"
            ),
            "alternatives": alternatives,
        }

    return {"field_values": field_values, "conflict_fields": conflict_fields}


def entity_key_for(member_ids: list[str]) -> str:
    digest = hashlib.sha1("|".join(sorted(member_ids)).encode("utf-8")).hexdigest()[:10].upper()
    return f"KH-{digest}"


def build_histogram(scores: list[float], bins: tuple[float, ...]) -> list[int]:
    """分数分布（10 个等宽桶，最后一个桶包含 1.0）。"""
    counts = [0] * (len(bins) - 1)
    for score in scores:
        position = int(score * (len(bins) - 1))
        position = min(position, len(counts) - 1)
        position = max(position, 0)
        counts[position] += 1
    return counts
