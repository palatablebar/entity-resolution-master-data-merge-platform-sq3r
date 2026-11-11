"""真实解析任务：worker 内执行 blocking + 打分 + 聚类 + golden record 仲裁并落库。"""
from __future__ import annotations

import uuid

from src.config.database import session_scope
from src.constants import error_codes as codes
from src.constants.enums import RunStatus
from src.models.merge_rule import MergeRule
from src.models.resolution_run import ResolutionRun
from src.services import resolution_service
from src.utils.errors import AppError
from src.utils.logger import get_logger
from worker_src.config.celery_app import celery_app

logger = get_logger("entresolv.worker.resolution")


@celery_app.task(bind=True, name="entresolv.resolve_run", max_retries=0)
def resolve_run(self, run_id: str) -> dict:
    logger.info("resolve_run start run=%s", run_id)
    with session_scope() as db:
        run = db.get(ResolutionRun, uuid.UUID(str(run_id)))
        if run is None:
            logger.warning("run not found run=%s", run_id)
            return {"ok": False, "reason": "run_not_found"}
        if run.status == RunStatus.SUCCEEDED.value:
            return {"ok": True, "reason": "already_succeeded"}

        rule = db.get(MergeRule, run.rule_id) if run.rule_id else None
        if rule is None:
            rule = resolution_service.default_rule(db)
        if rule is None:
            run.status = RunStatus.FAILED.value
            run.error_code = codes.RULE_INVALID
            run.error_message = "没有可用的合并规则"
            db.commit()
            return {"ok": False, "reason": "rule_missing"}

        try:
            resolution_service.execute_run(db, run, rule)
        except AppError as exc:
            logger.error("resolve_run failed run=%s code=%s error=%s", run_id, exc.code, exc.message)
            return {"ok": False, "reason": exc.code, "message": exc.message}
        except Exception as exc:  # noqa: BLE001
            logger.error("resolve_run crashed run=%s error=%s", run_id, exc, exc_info=True)
            return {"ok": False, "reason": "internal_error", "message": str(exc)}

        db.refresh(run)
        return {
            "ok": True,
            "run_id": str(run.id),
            "records": run.records_scanned,
            "candidates": run.candidate_pairs,
            "clusters_auto": run.clusters_auto,
            "clusters_review": run.clusters_review,
            "golden": run.golden_records,
            "duration_ms": run.duration_ms,
        }
