"""golden record controller：列表 / 详情 / CSV 导出。"""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from src.constants import error_codes as codes
from src.models.user import User
from src.services import audit_service, golden_service, run_service
from src.utils.errors import AppError


def list_golden(
    db: Session,
    *,
    run_id: str | None,
    query: str | None,
    status: str | None,
    cluster_id: str | None,
    page: int,
    page_size: int,
) -> dict:
    return golden_service.list_golden_records(
        db,
        run_id=run_id,
        query=query,
        status=status,
        cluster_id=cluster_id,
        page=page,
        page_size=page_size,
    )


def get_golden(db: Session, golden_id: str) -> dict:
    return golden_service.get_golden(db, golden_id)


def export_csv(
    db: Session, *, run_id: str | None, user: User, request: Request
) -> Response:
    target_run = run_id
    if not target_run:
        latest = run_service.latest_succeeded_run(db)
        if latest is None:
            raise AppError(codes.NOT_FOUND, "还没有成功的解析运行可导出", "no succeeded run")
        target_run = str(latest.id)
    content, filename = golden_service.export_csv(db, target_run)
    audit_service.record(
        db,
        action="golden.export",
        entity_type="GoldenRecord",
        entity_id=target_run,
        actor_id=str(user.id),
        actor_email=user.email,
        payload={"run_id": target_run, "rows": content.count("\n") - 1},
        ip=getattr(request.state, "client_ip", None),
        trace_id=getattr(request.state, "trace_id", None),
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
