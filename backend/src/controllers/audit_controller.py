"""审计日志 controller。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import audit_service


def list_logs(db: Session, *, limit: int, entity_type: str | None) -> dict:
    return {"items": audit_service.list_logs(db, limit=limit, entity_type=entity_type)}
