from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import record_controller
from src.constants.limits import PAGE_SIZE_DEFAULT
from src.middlewares.rbac import require_permission

router = APIRouter(prefix="/records", tags=["records"])


@router.get("")
def list_records(
    query: str | None = Query(default=None),
    source_system: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=100),
    user=Depends(require_permission("records:read")),
    db: Session = Depends(get_db),
) -> dict:
    return record_controller.list_records(
        db, query=query, source_system=source_system, page=page, page_size=page_size
    )


@router.get("/{record_id}")
def get_record(
    record_id: str,
    user=Depends(require_permission("records:read")),
    db: Session = Depends(get_db),
) -> dict:
    return record_controller.get_record(db, record_id)
