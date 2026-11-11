"""MergeRule 服务：读取、创建、更新与参数校验。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.constants.enums import SourceSystem
from src.constants.weights import DEFAULT_FIELD_WEIGHTS, DEFAULT_SOURCE_RELIABILITY
from src.models.merge_rule import MergeRule
from src.schemas.rules import RuleUpdateRequest, serialize_rule
from src.utils.errors import AppError, not_found
from src.utils.normalize import DEFAULT_NORMALIZATION


def ensure_default_rule(db: Session) -> MergeRule:
    rule = db.query(MergeRule).filter(MergeRule.is_active.is_(True)).order_by(MergeRule.created_at.asc()).first()
    if rule is not None:
        return rule
    rule = MergeRule(
        name="康和会员主数据 v1",
        field_weights=dict(DEFAULT_FIELD_WEIGHTS),
        source_reliability=dict(DEFAULT_SOURCE_RELIABILITY),
        auto_threshold=0.92,
        review_threshold=0.75,
        normalization=dict(DEFAULT_NORMALIZATION),
        is_active=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def list_rules(db: Session) -> list[dict[str, Any]]:
    rows = db.query(MergeRule).order_by(MergeRule.is_active.desc(), MergeRule.created_at.asc()).all()
    return [serialize_rule(row) for row in rows]


def get_rule(db: Session, rule_id: str) -> MergeRule:
    row = db.get(MergeRule, rule_id)
    if row is None:
        raise not_found("MergeRule", rule_id)
    return row


def create_rule(db: Session, name: str, auto_threshold: float, review_threshold: float) -> dict[str, Any]:
    if review_threshold >= auto_threshold:
        raise AppError(codes.RULE_INVALID, "review 阈值必须小于 auto 阈值", "review >= auto")
    if db.query(MergeRule).filter(MergeRule.name == name).first():
        raise AppError(codes.RULE_INVALID, "规则名已存在", f"name={name}")
    row = MergeRule(
        name=name,
        field_weights=dict(DEFAULT_FIELD_WEIGHTS),
        source_reliability=dict(DEFAULT_SOURCE_RELIABILITY),
        auto_threshold=auto_threshold,
        review_threshold=review_threshold,
        normalization=dict(DEFAULT_NORMALIZATION),
        is_active=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize_rule(row)


def _validate_weights(weights: dict[str, float]) -> dict[str, float]:
    allowed = set(DEFAULT_FIELD_WEIGHTS)
    if set(weights) - allowed:
        raise AppError(codes.RULE_INVALID, "包含未知字段权重", f"keys={sorted(set(weights) - allowed)}")
    cleaned: dict[str, float] = {}
    for field, value in weights.items():
        numeric = float(value)
        if numeric < 0 or numeric > 1:
            raise AppError(codes.RULE_INVALID, f"字段 {field} 权重必须在 0~1", f"value={numeric}")
        cleaned[field] = round(numeric, 4)
    if sum(cleaned.values()) <= 0:
        raise AppError(codes.RULE_INVALID, "字段权重之和必须大于 0", "sum=0")
    return cleaned


def _validate_reliability(values: dict[str, float]) -> dict[str, float]:
    allowed = {system.value for system in SourceSystem}
    if set(values) - allowed:
        raise AppError(codes.RULE_INVALID, "包含未知来源权重", f"keys={sorted(set(values) - allowed)}")
    cleaned: dict[str, float] = {}
    for source, value in values.items():
        numeric = float(value)
        if numeric < 0 or numeric > 1:
            raise AppError(codes.RULE_INVALID, f"来源 {source} 权重必须在 0~1", f"value={numeric}")
        cleaned[source] = round(numeric, 4)
    return cleaned


def update_rule(db: Session, rule_id: str, payload: RuleUpdateRequest) -> dict[str, Any]:
    row = get_rule(db, rule_id)
    if payload.field_weights is not None:
        row.field_weights = _validate_weights(payload.field_weights)
    if payload.source_reliability is not None:
        row.source_reliability = _validate_reliability(payload.source_reliability)
    if payload.auto_threshold is not None:
        row.auto_threshold = round(float(payload.auto_threshold), 4)
    if payload.review_threshold is not None:
        row.review_threshold = round(float(payload.review_threshold), 4)
    if row.review_threshold >= row.auto_threshold:
        raise AppError(codes.RULE_INVALID, "review 阈值必须小于 auto 阈值", "review >= auto")
    if payload.is_active is not None:
        if payload.is_active:
            db.query(MergeRule).filter(MergeRule.id != row.id).update({MergeRule.is_active: False})
        row.is_active = payload.is_active
    row.version += 1
    db.commit()
    db.refresh(row)
    return serialize_rule(row)


def snapshot(db: Session, rule: MergeRule) -> dict[str, Any]:
    """运行参数快照，写进 ResolutionRun.params_json。"""
    return {
        "rule_id": str(rule.id),
        "rule_name": rule.name,
        "rule_version": rule.version,
        "field_weights": dict(rule.field_weights),
        "source_reliability": dict(rule.source_reliability),
        "auto_threshold": rule.auto_threshold,
        "review_threshold": rule.review_threshold,
    }
