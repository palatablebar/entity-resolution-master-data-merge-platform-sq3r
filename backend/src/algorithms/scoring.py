"""算法 1b：字段级加权相似度打分。

特征：
  name    → Jaro-Winkler（自实现）
  phone   → 归一化精确匹配
  email   → 归一化精确匹配
  address → 分词 Token Jaccard（中文 2-gram + 拉丁词）
权重来自 MergeRule.field_weights；缺失字段按可用权重重新归一分母（不把缺失当 0 分）。
判定：score >= auto_threshold → auto；>= review_threshold → review；否则 reject。
"""
from __future__ import annotations

from typing import Any

from src.algorithms.types import RecordView
from src.constants.enums import CandidateDecision
from src.utils.similarity import jaro_winkler, normalized_exact, token_jaccard

FIELD_METHODS: dict[str, str] = {
    "name": "jaro_winkler",
    "phone": "normalized_exact",
    "email": "normalized_exact",
    "address": "token_jaccard",
}


def _field_similarity(field: str, left: RecordView, right: RecordView) -> float | None:
    if field == "name":
        if not left.normalized_name or not right.normalized_name:
            return None
        return jaro_winkler(left.normalized_name, right.normalized_name)
    if field == "phone":
        return normalized_exact(left.normalized_phone, right.normalized_phone)
    if field == "email":
        return normalized_exact(left.normalized_email, right.normalized_email)
    if field == "address":
        return token_jaccard(left.address_tokens(), right.address_tokens())
    return None


def _display_value(field: str, record: RecordView) -> str | None:
    return {
        "name": record.full_name,
        "phone": record.phone,
        "email": record.email,
        "address": record.address,
    }.get(field)


def score_pair(
    left: RecordView,
    right: RecordView,
    field_weights: dict[str, float],
    auto_threshold: float,
    review_threshold: float,
) -> dict[str, Any]:
    features: dict[str, dict[str, Any]] = {}
    numerator = 0.0
    available_weight = 0.0
    for field, weight in field_weights.items():
        similarity = _field_similarity(field, left, right)
        contribution = 0.0
        if similarity is not None:
            contribution = weight * similarity
            numerator += contribution
            available_weight += weight
        features[field] = {
            "field": field,
            "method": FIELD_METHODS.get(field, "unknown"),
            "weight": round(weight, 4),
            "left_value": _display_value(field, left),
            "right_value": _display_value(field, right),
            "similarity": round(similarity, 4) if similarity is not None else None,
            "contribution": round(contribution, 4),
        }

    score = round(numerator / available_weight, 4) if available_weight > 0 else 0.0
    if score >= auto_threshold:
        decision = CandidateDecision.AUTO.value
    elif score >= review_threshold:
        decision = CandidateDecision.REVIEW.value
    else:
        decision = CandidateDecision.REJECT.value

    return {
        "score": score,
        "decision": decision,
        "features": features,
        "available_weight": round(available_weight, 4),
        "thresholds": {"auto": auto_threshold, "review": review_threshold},
    }
