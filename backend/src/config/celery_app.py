"""Celery 客户端（backend 只投递任务，消费在 worker 容器）。"""
from __future__ import annotations

from celery import Celery

from src.config.settings import settings

celery_app = Celery(
    "entresolv",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)

TASK_RESOLVE_RUN = "entresolv.resolve_run"
