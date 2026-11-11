"""通用 schema 与分页结构。"""
from __future__ import annotations

import math
from typing import Any

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")


class ErrorOut(BaseModel):
    code: str
    message: str
    detail: str = ""
    trace_id: str | None = None
    extra: dict[str, Any] = {}


class OkOut(BaseModel):
    ok: bool = True
    message: str = ""


def page_payload(items: list[Any], page: int, page_size: int, total: int) -> dict[str, Any]:
    total_pages = max(1, math.ceil(total / page_size)) if total else 1
    return {
        "items": items,
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": total_pages,
    }
