"""来源记录 controller。"""
from __future__ import annotations

from sqlalchemy.orm import Session

from src.services import record_service


def list_records(
    db: Session, *, query: str | None, source_system: str | None, page: int, page_size: int
) -> dict:
    return record_service.list_records(
        db, query=query, source_system=source_system, page=page, page_size=page_size
    )


def get_record(db: Session, record_id: str) -> dict:
    return record_service.get_record(db, record_id)
