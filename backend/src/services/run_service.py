"""解析运行服务：创建并投递 Celery、查询列表与详情。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.config.celery_app import TASK_RESOLVE_RUN, celery_app
from src.constants import error_codes as codes
from src.constants.enums import RunStatus
from src.models.resolution_run import ResolutionRun
from src.models.user import User
from src.schemas.runs import serialize_run
from src.services import audit_service, rule_service
from src.utils.errors import AppError, not_found
from src.utils.logger import get_logger
from src.utils.pagination import normalize_page

logger = get_logger("entresolv.run")

ACTIVE_STATUSES = (RunStatus.QUEUED.value, RunStatus.RUNNING.value)


def list_runs(db: Session, *, status: str | None, page: int, page_size: int) -> dict[str, Any]:
    safe_page, safe_size = normalize_page(page, page_size)
    query = db.query(ResolutionRun)
    if status:
        query = query.filter(ResolutionRun.status == status)
    total = query.with_entities(func.count(ResolutionRun.id)).scalar() or 0
    rows = (
        query.order_by(ResolutionRun.created_at.desc())
        .offset((safe_page - 1) * safe_size)
        .limit(safe_size)
        .all()
    )
    return {
        "items": [serialize_run(row) for row in rows],
        "page": safe_page,
        "page_size": safe_size,
        "total": total,
        "total_pages": max(1, -(-total // safe_size)) if total else 1,
    }


def get_run(db: Session, run_id: str) -> Any:
    row = db.get(ResolutionRun, run_id)
    if row is None:
        raise not_found("ResolutionRun", run_id)
    return row


def latest_succeeded_run(db: Session) -> ResolutionRun | None:
    return (
        db.query(ResolutionRun)
        .filter(ResolutionRun.status == RunStatus.SUCCEEDED.value)
        .order_by(ResolutionRun.created_at.desc())
        .first()
    )


def create_run(
    db: Session,
    *,
    user: User,
    rule_id: str | None,
    run_label: str,
    ip: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    active = db.query(ResolutionRun).filter(ResolutionRun.status.in_(ACTIVE_STATUSES)).first()
    if active is not None:
        raise AppError(
            codes.RUN_CONFLICT,
            "已有解析任务在排队或运行中，请稍后重试",
            f"active_run={active.id}",
            extra={"active_run_id": str(active.id)},
        )

    if rule_id:
        rule = rule_service.get_rule(db, rule_id)
    else:
        rule = rule_service.ensure_default_rule(db)

    run = ResolutionRun(
        rule_id=rule.id,
        run_label=run_label or f"人工触发 · {rule.name}",
        status=RunStatus.QUEUED.value,
        params_json=rule_service.snapshot(db, rule),
        blocking_keys=["phone_suffix", "name_city", "email_domain"],
        triggered_by=user.id,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    audit_service.record(
        db,
        action="run.create",
        entity_type="ResolutionRun",
        entity_id=str(run.id),
        actor_id=str(user.id),
        actor_email=user.email,
        payload={"rule_id": str(rule.id), "run_label": run.run_label},
        ip=ip,
        trace_id=trace_id,
    )

    try:
        celery_app.send_task(TASK_RESOLVE_RUN, args=[str(run.id)])
        logger.info("run dispatched run=%s", run.id)
    except Exception as exc:  # noqa: BLE001
        logger.error("dispatch failed run=%s error=%s", run.id, exc)
        run.status = RunStatus.FAILED.value
        run.error_code = codes.INTERNAL_ERROR
        run.error_message = f"任务队列不可用：{exc}"[:500]
        db.commit()
        raise AppError(codes.INTERNAL_ERROR, "任务队列暂不可用，运行未启动", str(exc)) from exc

    return serialize_run(run)


def rerun(db: Session, run_id: str, *, user: User, ip: str | None, trace_id: str | None) -> dict[str, Any]:
    previous = get_run(db, run_id)
    return create_run(
        db,
        user=user,
        rule_id=str(previous.rule_id) if previous.rule_id else None,
        run_label=f"重跑 · {previous.run_label}"[:160],
        ip=ip,
        trace_id=trace_id,
    )
