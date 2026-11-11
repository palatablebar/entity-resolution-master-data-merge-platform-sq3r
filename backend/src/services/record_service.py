"""SourceRecord 查询服务。"""
from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from src.models.source_record import SourceRecord
from src.schemas.records import serialize_record
from src.utils.errors import not_found
from src.utils.pagination import normalize_page


def list_records(
    db: Session,
    *,
    query: str | None,
    source_system: str | None,
    page: int,
    page_size: int,
) -> dict:
    safe_page, safe_size = normalize_page(page, page_size)
    base = db.query(SourceRecord)
    if source_system:
        base = base.filter(SourceRecord.source_system == source_system)
    if query:
        pattern = f"%{query.strip()}%"
        base = base.filter(
            or_(
                SourceRecord.full_name.ilike(pattern),
                SourceRecord.phone.ilike(pattern),
                SourceRecord.email.ilike(pattern),
                SourceRecord.address.ilike(pattern),
                SourceRecord.external_id.ilike(pattern),
            )
        )
    total = base.with_entities(func.count(SourceRecord.id)).scalar() or 0
    rows = (
        base.order_by(SourceRecord.source_system.asc(), SourceRecord.external_id.asc())
        .offset((safe_page - 1) * safe_size)
        .limit(safe_size)
        .all()
    )
    return {
        "items": [serialize_record(row) for row in rows],
        "page": safe_page,
        "page_size": safe_size,
        "total": total,
        "total_pages": max(1, -(-total // safe_size)) if total else 1,
    }


def get_record(db: Session, record_id: str) -> dict:
    row = db.get(SourceRecord, record_id)
    if row is None:
        raise not_found("SourceRecord", record_id)
    return serialize_record(row, include_raw=True)
