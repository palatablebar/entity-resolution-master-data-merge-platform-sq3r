"""规则 controller：列表 / 创建 / 更新。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.rules import RuleCreateRequest, RuleUpdateRequest
from src.services import audit_service, rule_service


def list_rules(db: Session) -> dict:
    rule_service.ensure_default_rule(db)
    return {"items": rule_service.list_rules(db)}


def create_rule(db: Session, payload: RuleCreateRequest, *, user: User, request: Request) -> dict:
    result = rule_service.create_rule(
        db, payload.name, payload.auto_threshold, payload.review_threshold
    )
    audit_service.record(
        db,
        action="rule.create",
        entity_type="MergeRule",
        entity_id=result["id"],
        actor_id=str(user.id),
        actor_email=user.email,
        payload={"name": result["name"]},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return result


def update_rule(
    db: Session, rule_id: str, payload: RuleUpdateRequest, *, user: User, request: Request
) -> dict:
    before = rule_service.get_rule(db, rule_id)
    previous_version = before.version
    result = rule_service.update_rule(db, rule_id, payload)
    audit_service.record(
        db,
        action="rule.update",
        entity_type="MergeRule",
        entity_id=rule_id,
        actor_id=str(user.id),
        actor_email=user.email,
        payload={
            "from_version": previous_version,
            "to_version": result["version"],
            "changes": payload.model_dump(exclude_none=True),
        },
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return result
