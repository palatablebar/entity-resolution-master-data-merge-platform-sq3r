"""分页参数规范化。"""
from __future__ import annotations

from src.constants.limits import PAGE_SIZE_DEFAULT, PAGE_SIZE_MAX


def normalize_page(page: int | None, page_size: int | None) -> tuple[int, int]:
    safe_page = max(1, int(page or 1))
    safe_size = int(page_size or PAGE_SIZE_DEFAULT)
    safe_size = max(1, min(safe_size, PAGE_SIZE_MAX))
    return safe_page, safe_size
