"""路由总装配。"""
from fastapi import APIRouter

from src.routes import (
    audit,
    auth,
    candidate,
    cluster,
    golden,
    health,
    meta,
    record,
    rule,
    run,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(meta.router)
api_router.include_router(record.router)
api_router.include_router(candidate.router)
api_router.include_router(cluster.router)
api_router.include_router(golden.router)
api_router.include_router(rule.router)
api_router.include_router(run.router)
api_router.include_router(audit.router)

__all__ = ["api_router"]
