"""候选对 controller：列表 / 详情 / 复核。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.models.user import User
from src.services import candidate_service


def list_candidates(
    db: Session,
    *,
    run_id: str | None,
    decision: str | None,
    status: str | None,
    page: int,
    page_size: int,
) -> dict:
    return candidate_service.list_candidates(
        db, run_id=run_id, decision=decision, status=status, page=page, page_size=page_size
    )


def get_candidate(db: Session, candidate_id: str) -> dict:
    return candidate_service.get_candidate(db, candidate_id)


def review_candidate(
    db: Session, candidate_id: str, *, action: str, note: str, user: User, request: Request
) -> dict:
    return candidate_service.review_candidate(
        db,
        candidate_id,
        action=action,
        note=note,
        user=user,
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
