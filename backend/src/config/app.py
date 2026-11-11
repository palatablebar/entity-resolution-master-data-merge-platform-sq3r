"""FastAPI 应用装配：中间件、异常处理、路由挂载、启动 seed。"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import settings
from src.middlewares.audit_context import AuditContextMiddleware
from src.middlewares.error_handler import register_exception_handlers
from src.routes import api_router

logger = logging.getLogger("entresolv.app")


def _run_seed_once() -> None:
    if not settings.seed_demo:
        return
    try:
        from scripts.seed_demo import seed_all

        result = seed_all()
        logger.warning(
            "[SEED_DEMO] seed finished created=%s skipped=%s summary=%s",
            result.get("created", 0),
            result.get("skipped", 0),
            result.get("summary", {}),
        )
    except Exception as exc:  # noqa: BLE001 - 启动阶段不允许阻塞健康检查
        logger.warning("[SEED_DEMO] seed failed (ignored): %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _run_seed_once()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="entresolv · 实体解析与主数据合并台", version="1.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(AuditContextMiddleware)
    register_exception_handlers(app)

    # 同一份路由挂两次：/api/* 供直连与健康检查；根路径供 Nginx 剥掉 /api 后反代
    app.include_router(api_router, prefix="/api")
    app.include_router(api_router, include_in_schema=False)
    return app
