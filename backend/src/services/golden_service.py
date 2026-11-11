"""golden record 服务：列表、详情、CSV 导出。"""
from __future__ import annotations

import csv
import io
import uuid
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.constants.enums import FIELD_LABELS
from src.models.entity_cluster import EntityCluster
from src.models.golden_record import GoldenRecord
from src.schemas.golden import serialize_golden
from src.utils.errors import not_found
from src.utils.pagination import normalize_page

EXPORT_FIELDS = ("name", "phone", "email", "address")
EXPORT_HEADERS = ["entity_key", "置信度", "状态", "姓名", "手机", "邮箱", "地址", "冲突字段", "来源引用"]


def list_golden_records(
    db: Session,
    *,
    run_id: str | None,
    query: str | None,
    status: str | None,
    cluster_id: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    safe_page, safe_size = normalize_page(page, page_size)
    base = db.query(GoldenRecord)
    if run_id:
        base = base.filter(GoldenRecord.run_id == run_id)
    if cluster_id:
        base = base.filter(GoldenRecord.cluster_id == cluster_id)
    if status:
        base = base.filter(GoldenRecord.status == status)
    if query:
        pattern = f"%{query.strip()}%"
        base = base.filter(GoldenRecord.entity_key.ilike(pattern))
    total = base.with_entities(func.count(GoldenRecord.id)).scalar() or 0
    rows = (
        base.order_by(GoldenRecord.confidence.desc(), GoldenRecord.entity_key.asc())
        .offset((safe_page - 1) * safe_size)
        .limit(safe_size)
        .all()
    )
    items = []
    for row in rows:
        payload = serialize_golden(row)
        payload["display"] = {
            field: (row.field_values.get(field) or {}).get("value") for field in EXPORT_FIELDS
        }
        items.append(payload)
    return {
        "items": items,
        "page": safe_page,
        "page_size": safe_size,
        "total": total,
        "total_pages": max(1, -(-total // safe_size)) if total else 1,
    }


def get_golden(db: Session, golden_id: str) -> dict[str, Any]:
    row = db.get(GoldenRecord, golden_id)
    if row is None:
        raise not_found("GoldenRecord", golden_id)
    cluster = db.get(EntityCluster, row.cluster_id)
    return serialize_golden(row, cluster=cluster)


def export_csv(db: Session, run_id: str) -> tuple[str, str]:
    """返回 (CSV 文本, 文件名)。字段口径固定，供营销系统直接导入。"""
    rows = (
        db.query(GoldenRecord)
        .filter(GoldenRecord.run_id == run_id)
        .order_by(GoldenRecord.entity_key.asc())
        .all()
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_HEADERS)
    for row in rows:
        values = row.field_values or {}
        references = []
        for field in EXPORT_FIELDS:
            detail = values.get(field) or {}
            if detail.get("source_system"):
                references.append(f"{FIELD_LABELS.get(field, field)}:{detail.get('source_system')}")
        writer.writerow(
            [
                row.entity_key,
                f"{row.confidence:.4f}",
                row.status,
                (values.get("name") or {}).get("value") or "",
                (values.get("phone") or {}).get("value") or "",
                (values.get("email") or {}).get("value") or "",
                (values.get("address") or {}).get("value") or "",
                "|".join(row.conflict_fields or []),
                "|".join(references),
            ]
        )
    filename = f"golden_records_{str(run_id)[:8]}.csv"
    return buffer.getvalue(), filename
