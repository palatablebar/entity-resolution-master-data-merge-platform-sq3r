"""运行 controller：列表 / 详情 / 触发 / 重跑。"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from src.models.user import User
from src.schemas.runs import RunCreateRequest, serialize_run
from src.services import run_service


def list_runs(db: Session, *, status: str | None, page: int, page_size: int) -> dict:
    return run_service.list_runs(db, status=status, page=page, page_size=page_size)


def get_run(db: Session, run_id: str) -> dict:
    return serialize_run(run_service.get_run(db, run_id))


def create_run(
    db: Session, payload: RunCreateRequest, *, user: User, request: Request
) -> dict:
    return run_service.create_run(
        db,
        user=user,
        rule_id=payload.rule_id,
        run_label=payload.run_label,
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )


def rerun(db: Session, run_id: str, *, user: User, request: Request) -> dict:
    return run_service.rerun(
        db,
        run_id,
        user=user,
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
