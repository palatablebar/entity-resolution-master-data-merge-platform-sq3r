"""人工重新成组纯函数单测：python -m unittest tests.test_regroup（仅标准库）。

覆盖需求口径：
  - 确认一对 ≠ 整簇同人：confirmed 组只含已确认成员，未决记录保持待定；
  - 拒绝的关系不能留在同一身份（守卫 409 + 计划兜底拆分）；
  - 同一判断重复执行结果一致（幂等，不新增分组）。
"""
from __future__ import annotations

import unittest

from src.algorithms.regroup import (
    GROUP_CONFIRMED,
    GROUP_PENDING,
    ScopeEdge,
    build_regroup_plan,
    check_judgment,
    collect_scope,
)

A, B, C, D, Z = "rec-a", "rec-b", "rec-c", "rec-d", "rec-z"


def edge(
    left: str,
    right: str,
    score: float = 0.85,
    decision: str = "review",
    status: str = "pending",
    cid: str | None = None,
) -> ScopeEdge:
    return ScopeEdge(
        candidate_id=cid or f"cand-{left}-{right}",
        left_id=left,
        right_id=right,
        score=score,
        decision=decision,
        status=status,
    )


def triangle(status_ab="pending", status_ac="pending", status_bc="pending") -> list[ScopeEdge]:
    return [
        edge(A, B, 0.88, status=status_ab, cid="cand-ab"),
        edge(A, C, 0.86, status=status_ac, cid="cand-ac"),
        edge(B, C, 0.84, status=status_bc, cid="cand-bc"),
    ]


def group_members(plan, kind):
    return sorted(tuple(g.members) for g in plan.groups if g.kind == kind)


class CollectScopeTest(unittest.TestCase):
    def test_scope_follows_auto_and_review_edges_only(self):
        edges = triangle() + [
            edge(A, Z, 0.40, decision="reject", cid="cand-az"),  # 系统拒绝边不扩散作用域
            edge(C, D, 0.90, decision="auto", cid="cand-cd"),
        ]
        scope = collect_scope(A, B, edges)
        self.assertEqual(scope, {A, B, C, D})
        self.assertNotIn(Z, scope)


class ConfirmRegroupTest(unittest.TestCase):
    def test_confirm_one_pair_does_not_merge_whole_cluster(self):
        """确认 A-B 后：{A,B} 成身份，C 保持待定（单成员待定组），待定关系保留。"""
        edges = triangle(status_ab="confirmed")
        plan = build_regroup_plan({A, B, C}, edges)

        self.assertEqual(group_members(plan, GROUP_CONFIRMED), [(A, B)])
        self.assertEqual(group_members(plan, GROUP_PENDING), [(C,)])
        pending_pairs = {e.pair() for e in plan.pending_edges}
        self.assertEqual(pending_pairs, {(A, C), (B, C)})

    def test_confirm_bridge_merges_singleton_into_identity(self):
        """再确认 B-C 后：C 并入，得到唯一身份 {A,B,C}，无待定组；
        尚未落章的 A-C 仍是待定关系（挂在身份内，等待人工处理）。"""
        edges = triangle(status_ab="confirmed", status_bc="confirmed")
        plan = build_regroup_plan({A, B, C}, edges)

        self.assertEqual(group_members(plan, GROUP_CONFIRMED), [(A, B, C)])
        self.assertEqual(group_members(plan, GROUP_PENDING), [])
        self.assertEqual([e.candidate_id for e in plan.pending_edges], ["cand-ac"])

    def test_auto_edges_join_confirmed_identity(self):
        edges = [
            edge(A, B, 0.97, decision="auto", cid="cand-ab"),
            edge(B, C, 0.83, status="confirmed", cid="cand-bc"),
            edge(C, D, 0.81, status="pending", cid="cand-cd"),
        ]
        plan = build_regroup_plan({A, B, C, D}, edges)

        self.assertEqual(group_members(plan, GROUP_CONFIRMED), [(A, B, C)])
        self.assertEqual(group_members(plan, GROUP_PENDING), [(D,)])

    def test_confirmed_group_confidence_is_weakest_edge(self):
        edges = triangle(status_ab="confirmed")
        plan = build_regroup_plan({A, B, C}, edges)
        confirmed = plan.confirmed_groups[0]
        self.assertEqual(confirmed.confidence, 0.88)
        singleton = plan.pending_groups[0]
        self.assertEqual(singleton.confidence, 0.0)


class RejectRegroupTest(unittest.TestCase):
    def test_rejected_pair_not_kept_in_same_pending_group(self):
        """拒绝 A-B 后：A、B 不得留在同一组；待定组绕开已拒绝对。"""
        edges = triangle(status_ab="rejected")
        plan = build_regroup_plan({A, B, C}, edges)

        self.assertEqual(group_members(plan, GROUP_CONFIRMED), [])
        pending = group_members(plan, GROUP_PENDING)
        self.assertEqual(pending, [(A, C), (B,)])
        for group in plan.groups:
            self.assertFalse({A, B} <= set(group.members), "已拒绝对不得同组")

    def test_all_rejected_leaves_no_groups(self):
        edges = triangle(status_ab="rejected", status_ac="rejected", status_bc="rejected")
        plan = build_regroup_plan({A, B, C}, edges)

        self.assertEqual(plan.groups, [])
        self.assertEqual(plan.pending_edges, [])

    def test_legacy_contradiction_falls_back_to_rejection_wins(self):
        """历史遗留矛盾（A-B、B-C 已确认但 A-C 已拒绝）：兜底保证 A、C 不同身份。"""
        edges = triangle(status_ab="confirmed", status_bc="confirmed", status_ac="rejected")
        plan = build_regroup_plan({A, B, C}, edges)

        for group in plan.confirmed_groups:
            self.assertFalse({A, C} <= set(group.members), "已拒绝对不得留在同一身份")


class JudgmentGuardTest(unittest.TestCase):
    def test_reject_inside_confirmed_identity_is_blocked(self):
        edges = triangle(status_ab="confirmed", status_bc="confirmed")
        reason = check_judgment("reject", A, C, edges)
        self.assertIsNotNone(reason)

    def test_confirm_that_would_trap_rejected_pair_is_blocked(self):
        edges = triangle(status_ab="confirmed", status_ac="rejected")
        reason = check_judgment("confirm", B, C, edges)
        self.assertIsNotNone(reason)

    def test_consistent_judgments_pass(self):
        edges = triangle(status_ab="confirmed")
        self.assertIsNone(check_judgment("confirm", B, C, edges))
        self.assertIsNone(check_judgment("reject", A, C, edges))

    def test_system_reject_decision_does_not_block_confirm(self):
        """decision=reject（系统低分）不是人工拒绝，不构成硬约束。"""
        edges = triangle(status_ab="confirmed") + [
            edge(A, Z, 0.30, decision="reject", cid="cand-az"),
            edge(B, Z, 0.80, status="pending", cid="cand-bz"),
        ]
        self.assertIsNone(check_judgment("confirm", B, Z, edges))


class IdempotencyTest(unittest.TestCase):
    def test_same_inputs_same_plan(self):
        edges = triangle(status_ab="confirmed")
        first = build_regroup_plan({A, B, C}, edges)
        second = build_regroup_plan({A, B, C}, edges)

        self.assertEqual(
            [(g.kind, g.members, g.confidence) for g in first.groups],
            [(g.kind, g.members, g.confidence) for g in second.groups],
        )
        self.assertEqual(
            [e.candidate_id for e in first.pending_edges],
            [e.candidate_id for e in second.pending_edges],
        )

    def test_repeated_confirm_is_stable(self):
        """重复执行同一判断（重放）不产生新分组。"""
        once = build_regroup_plan({A, B, C}, triangle(status_ab="confirmed"))
        twice = build_regroup_plan({A, B, C}, triangle(status_ab="confirmed"))
        self.assertEqual(
            [(g.kind, tuple(g.members)) for g in once.groups],
            [(g.kind, tuple(g.members)) for g in twice.groups],
        )


def apply(edges: list[ScopeEdge], cid: str, status: str) -> list[ScopeEdge]:
    """模拟服务层落章：把指定候选改成新状态后返回新边集。"""
    return [
        ScopeEdge(e.candidate_id, e.left_id, e.right_id, e.score, e.decision, status if e.candidate_id == cid else e.status)
        for e in edges
    ]


class ReviewSessionTrajectoryTest(unittest.TestCase):
    """模拟多次落章的完整轨迹（服务层每次落章都会重算一次计划）。"""

    def test_confirm_all_three_converges_to_single_identity(self):
        edges = triangle()
        plan = build_regroup_plan({A, B, C}, edges)
        self.assertEqual(group_members(plan, GROUP_PENDING), [(A, B, C)])

        edges = apply(edges, "cand-ab", "confirmed")
        plan = build_regroup_plan({A, B, C}, edges)
        self.assertEqual(group_members(plan, GROUP_CONFIRMED), [(A, B)])
        self.assertEqual(group_members(plan, GROUP_PENDING), [(C,)])

        edges = apply(edges, "cand-ac", "confirmed")
        plan = build_regroup_plan({A, B, C}, edges)
        self.assertEqual(group_members(plan, GROUP_CONFIRMED), [(A, B, C)])
        self.assertEqual(group_members(plan, GROUP_PENDING), [])

        edges = apply(edges, "cand-bc", "confirmed")
        plan = build_regroup_plan({A, B, C}, edges)
        self.assertEqual(group_members(plan, GROUP_CONFIRMED), [(A, B, C)])
        self.assertEqual(len(plan.groups), 1, "第三次确认不新增分组")

    def test_reject_all_three_dissolves_everything(self):
        edges = triangle()
        edges = apply(edges, "cand-ab", "rejected")
        plan = build_regroup_plan({A, B, C}, edges)
        self.assertEqual(group_members(plan, GROUP_CONFIRMED), [])
        for group in plan.groups:
            self.assertFalse({A, B} <= set(group.members))

        edges = apply(edges, "cand-ac", "rejected")
        plan = build_regroup_plan({A, B, C}, edges)
        self.assertEqual(group_members(plan, GROUP_PENDING), [(B, C)])

        edges = apply(edges, "cand-bc", "rejected")
        plan = build_regroup_plan({A, B, C}, edges)
        self.assertEqual(plan.groups, [])
        self.assertEqual(plan.pending_edges, [])

    def test_confirm_then_reject_then_blocked_confirm(self):
        edges = triangle()
        edges = apply(edges, "cand-ab", "confirmed")
        self.assertIsNone(check_judgment("reject", A, C, edges))
        edges = apply(edges, "cand-ac", "rejected")
        # B-C 仍未决：C 保持待定，不并入 {A,B}
        plan = build_regroup_plan({A, B, C}, edges)
        self.assertEqual(group_members(plan, GROUP_CONFIRMED), [(A, B)])
        self.assertEqual(group_members(plan, GROUP_PENDING), [(C,)])
        # 再确认 B-C 会把已拒绝的 A-C 圈进同一身份 → 守卫拦截
        self.assertIsNotNone(check_judgment("confirm", B, C, edges))


if __name__ == "__main__":
    unittest.main()
