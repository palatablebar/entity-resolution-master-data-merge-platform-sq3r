"""健康检查与概览 controller。"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.services import meta_service


def health(db: Session) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ok", "service": "entresolv-backend"}


def overview(db: Session) -> dict:
    return meta_service.overview(db)
