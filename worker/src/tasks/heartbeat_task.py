"""心跳任务：写 Redis 时间戳，worker healthcheck 依赖它。"""
from __future__ import annotations

import time

from src.utils.logger import get_logger
from src.utils.redis_client import get_redis
from worker_src.config.celery_app import celery_app

logger = get_logger("entresolv.worker.heartbeat")


@celery_app.task(name="entresolv.heartbeat")
def heartbeat() -> dict:
    timestamp = time.time()
    try:
        get_redis().set("entresolv:worker:heartbeat", f"{timestamp:.3f}", ex=300)
    except Exception as exc:  # noqa: BLE001
        logger.warning("heartbeat failed: %s", exc)
        return {"ok": False, "at": timestamp}
    return {"ok": True, "at": timestamp}
