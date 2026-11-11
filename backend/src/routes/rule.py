from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import rule_controller
from src.middlewares.rbac import require_permission
from src.schemas.rules import RuleCreateRequest, RuleUpdateRequest

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("")
def list_rules(
    user=Depends(require_permission("rules:read")), db: Session = Depends(get_db)
) -> dict:
    return rule_controller.list_rules(db)


@router.post("")
def create_rule(
    payload: RuleCreateRequest,
    request: Request,
    user=Depends(require_permission("rules:write")),
    db: Session = Depends(get_db),
) -> dict:
    return rule_controller.create_rule(db, payload, user=user, request=request)


@router.patch("/{rule_id}")
def update_rule(
    rule_id: str,
    payload: RuleUpdateRequest,
    request: Request,
    user=Depends(require_permission("rules:write")),
    db: Session = Depends(get_db),
) -> dict:
    return rule_controller.update_rule(db, rule_id, payload, user=user, request=request)
