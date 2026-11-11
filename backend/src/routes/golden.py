from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import golden_controller
from src.constants.limits import PAGE_SIZE_DEFAULT
from src.middlewares.rbac import require_permission

router = APIRouter(prefix="/golden", tags=["golden"])


@router.get("/export")
def export_csv(
    request: Request,
    run_id: str | None = Query(default=None),
    user=Depends(require_permission("golden:export")),
    db: Session = Depends(get_db),
):
    return golden_controller.export_csv(db, run_id=run_id, user=user, request=request)


@router.get("")
def list_golden(
    run_id: str | None = Query(default=None),
    query: str | None = Query(default=None),
    status: str | None = Query(default=None),
    cluster_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=100),
    user=Depends(require_permission("golden:read")),
    db: Session = Depends(get_db),
) -> dict:
    return golden_controller.list_golden(
        db,
        run_id=run_id,
        query=query,
        status=status,
        cluster_id=cluster_id,
        page=page,
        page_size=page_size,
    )


@router.get("/{golden_id}")
def get_golden(
    golden_id: str,
    user=Depends(require_permission("golden:read")),
    db: Session = Depends(get_db),
) -> dict:
    return golden_controller.get_golden(db, golden_id)
