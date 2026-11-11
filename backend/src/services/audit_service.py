"""审计日志写入与查询。"""
from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from src.models.audit_log import AuditLog


def record(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    actor_id: str | None = None,
    actor_email: str = "",
    payload: dict[str, Any] | None = None,
    ip: str | None = None,
    trace_id: str | None = None,
) -> None:
    db.add(
        AuditLog(
            actor_id=actor_id,
            actor_email=actor_email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=payload or {},
            ip=ip,
            trace_id=trace_id,
        )
    )
    db.commit()


def list_logs(db: Session, limit: int = 50, entity_type: str | None = None) -> list[dict[str, Any]]:
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    rows = query.order_by(AuditLog.created_at.desc()).limit(max(1, min(limit, 200))).all()
    return [
        {
            "id": str(row.id),
            "actor_id": str(row.actor_id) if row.actor_id else None,
            "actor_email": row.actor_email,
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "payload": row.payload_json,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
