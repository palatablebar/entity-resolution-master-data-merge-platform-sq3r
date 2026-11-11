"""人工复核后的重新成组（纯函数，与 ORM 解耦，便于单测）。

成组口径（每次落章后对整个受影响作用域重算，确定性、可幂等重放）：

  - **身份（confirmed 组）** = auto 边 ∪ 已确认 review 边的连通分量（≥2 条记录）。
    黄金档案只由这些已确认成员重建。
  - **已拒绝是硬约束**：同一身份绝不允许包含人工已拒绝的 pair。
    - `check_judgment` 在落章前拦截会产生矛盾的新判断（返回中文原因）；
    - `build_regroup_plan` 对历史遗留矛盾兜底：合并时跳过会把已拒绝 pair
      并入同一分量的边，保证拒绝关系永不留在同一身份。
  - **未决记录保持待定**：未进入任何身份的剩余记录里，仍有 pending review
    边的按 pending 边连通成待定组；与已确认成员之间只剩 pending 边的落单
    记录自成一组（单成员待定组）。
  - 全部关系都已落定的记录不再保留任何簇。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from src.algorithms.clustering import DisjointSet

DECISION_AUTO = "auto"
DECISION_REVIEW = "review"

STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_REJECTED = "rejected"

GROUP_CONFIRMED = "confirmed"
GROUP_PENDING = "pending"


@dataclass(frozen=True)
class ScopeEdge:
    """作用域内一条候选边（与 ORM 行解耦的最小视图）。"""

    candidate_id: str
    left_id: str
    right_id: str
    score: float
    decision: str  # auto / review / reject
    status: str  # pending / confirmed / rejected

    def pair(self) -> tuple[str, str]:
        return (self.left_id, self.right_id) if self.left_id < self.right_id else (self.right_id, self.left_id)


@dataclass
class RegroupGroup:
    """一个目标分组：confirmed 身份或 pending 待定组。"""

    kind: str  # GROUP_CONFIRMED / GROUP_PENDING
    members: list[str]  # 排序后的记录 id
    edges: list[ScopeEdge] = field(default_factory=list)  # 组内驱动边（算置信度用）

    @property
    def confidence(self) -> float:
        """簇置信度 = 组内驱动边最低分（最弱一环）；无驱动边（单成员待定组）为 0。"""
        if not self.edges:
            return 0.0
        return round(min(edge.score for edge in self.edges), 4)


@dataclass
class RegroupPlan:
    """一次重新成组的完整计划：目标分组 + 仍待定的关系。"""

    scope_record_ids: list[str]
    groups: list[RegroupGroup]
    pending_edges: list[ScopeEdge]  # 全作用域的待定关系（含指向已确认身份的）
    rejected_pairs: set[tuple[str, str]]

    @property
    def confirmed_groups(self) -> list[RegroupGroup]:
        return [group for group in self.groups if group.kind == GROUP_CONFIRMED]

    @property
    def pending_groups(self) -> list[RegroupGroup]:
        return [group for group in self.groups if group.kind == GROUP_PENDING]


def collect_scope(seed_left: str, seed_right: str, edges: list[ScopeEdge]) -> set[str]:
    """从被复核 pair 出发，沿 auto/review 边 BFS 出受影响的作用域记录集合。

    reject 判定的候选是系统级非匹配，不参与成组、也不扩散作用域。
    """
    adjacency: dict[str, list[str]] = {}
    for edge in edges:
        if edge.decision not in (DECISION_AUTO, DECISION_REVIEW):
            continue
        adjacency.setdefault(edge.left_id, []).append(edge.right_id)
        adjacency.setdefault(edge.right_id, []).append(edge.left_id)
    seen = {seed_left, seed_right}
    stack = [seed_left, seed_right]
    while stack:
        node = stack.pop()
        for nxt in adjacency.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return seen


def _union_edges(edges: list[ScopeEdge]) -> list[ScopeEdge]:
    """身份合并边：auto 边（系统已落定）+ 人工已确认的 review 边。"""
    return [e for e in edges if e.decision == DECISION_AUTO or e.status == STATUS_CONFIRMED]


def _rejected_pairs(edges: list[ScopeEdge]) -> set[tuple[str, str]]:
    return {e.pair() for e in edges if e.status == STATUS_REJECTED}


def _components_respecting_rejections(
    node_ids: set[str] | list[str],
    union_edges: list[ScopeEdge],
    rejected_pairs: set[tuple[str, str]],
) -> list[list[str]]:
    """并查集连通分量，但跳过任何会把已拒绝 pair 并入同一分量的合并。

    合并顺序确定：auto 边优先，其余按分数降序、候选 id 升序——保证可重放。
    """
    dsu = DisjointSet()
    for node in node_ids:
        dsu.find(node)

    ordered = sorted(
        union_edges,
        key=lambda e: (0 if e.decision == DECISION_AUTO else 1, -e.score, e.candidate_id),
    )
    for edge in ordered:
        root_left, root_right = dsu.find(edge.left_id), dsu.find(edge.right_id)
        if root_left == root_right:
            continue
        members_left = {n for n in dsu.parent if dsu.find(n) == root_left}
        members_right = {n for n in dsu.parent if dsu.find(n) == root_right}
        clashes = any(
            (left in members_left and right in members_right)
            or (left in members_right and right in members_left)
            for left, right in rejected_pairs
        )
        if clashes:
            continue  # 已拒绝的关系不能留在同一身份
        dsu.union(edge.left_id, edge.right_id)

    groups = [sorted(members) for members in dsu.components().values()]
    groups.sort(key=lambda members: (members[0], len(members)))
    return groups


def check_judgment(
    action: str,
    left_id: str,
    right_id: str,
    scope_edges: list[ScopeEdge],
) -> str | None:
    """落章前的矛盾守卫。返回 None 表示允许，否则返回中文冲突原因。

    - reject：该对已通过 auto/已确认边连成同一身份 → 拒绝会留下矛盾；
    - confirm：合并后会把某条人工已拒绝的 pair 圈进同一身份 → 冲突。
    """
    union = _union_edges(scope_edges)
    if action == "reject":
        dsu = DisjointSet()
        for edge in union:
            dsu.union(edge.left_id, edge.right_id)
        if dsu.find(left_id) == dsu.find(right_id):
            return "该对记录已通过已确认关系并入同一身份，无法拒绝；请先复核相关确认记录"
        return None

    dsu = DisjointSet()
    for edge in union:
        dsu.union(edge.left_id, edge.right_id)
    dsu.union(left_id, right_id)  # 模拟本次确认生效后的身份
    for edge in scope_edges:
        if edge.status == STATUS_REJECTED and dsu.find(edge.left_id) == dsu.find(edge.right_id):
            return "确认后会把一条已拒绝的关系圈进同一身份；请先复核此前被拒绝的候选"
    return None


def build_regroup_plan(scope_ids: set[str], edges: list[ScopeEdge]) -> RegroupPlan:
    """对作用域重算目标分组。输入相同则输出相同（幂等、可重放）。"""
    scope_edges = [e for e in edges if e.left_id in scope_ids and e.right_id in scope_ids]
    rejected = _rejected_pairs(scope_edges)
    union = _union_edges(scope_edges)

    groups: list[RegroupGroup] = []

    # 1) 已确认身份：auto ∪ confirmed 连通分量（≥2），拒绝约束兜底
    confirmed_components = [
        component
        for component in _components_respecting_rejections(sorted(scope_ids), union, rejected)
        if len(component) >= 2
    ]
    confirmed_members: set[str] = set()
    for members in confirmed_components:
        member_set = set(members)
        inside = [e for e in union if e.left_id in member_set and e.right_id in member_set]
        groups.append(RegroupGroup(GROUP_CONFIRMED, members, inside))
        confirmed_members.update(member_set)

    # 2) 未决记录保持待定：剩余记录按 pending review 边连通成组
    leftovers = sorted(scope_ids - confirmed_members)
    leftover_set = set(leftovers)
    pending_edges = [
        e for e in scope_edges if e.decision == DECISION_REVIEW and e.status == STATUS_PENDING
    ]
    pending_within = [e for e in pending_edges if e.left_id in leftover_set and e.right_id in leftover_set]
    pending_components = [
        component
        for component in _components_respecting_rejections(leftover_set, pending_within, rejected)
        if len(component) >= 2
    ]
    grouped_pending: set[str] = set()
    for members in pending_components:
        member_set = set(members)
        inside = [e for e in pending_within if e.left_id in member_set and e.right_id in member_set]
        groups.append(RegroupGroup(GROUP_PENDING, members, inside))
        grouped_pending.update(member_set)

    # 3) 与已确认身份之间只剩 pending 边的落单记录 → 单成员待定组
    pending_has_edge: set[str] = set()
    for edge in pending_edges:
        pending_has_edge.add(edge.left_id)
        pending_has_edge.add(edge.right_id)
    for record_id in leftovers:
        if record_id not in grouped_pending and record_id in pending_has_edge:
            groups.append(RegroupGroup(GROUP_PENDING, [record_id], []))

    groups.sort(key=lambda g: (0 if g.kind == GROUP_CONFIRMED else 1, g.members))
    return RegroupPlan(
        scope_record_ids=sorted(scope_ids),
        groups=groups,
        pending_edges=sorted(pending_edges, key=lambda e: (-e.score, e.candidate_id)),
        rejected_pairs=rejected,
    )
