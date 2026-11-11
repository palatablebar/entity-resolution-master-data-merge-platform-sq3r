from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import cluster_controller
from src.constants.limits import PAGE_SIZE_DEFAULT
from src.middlewares.rbac import require_permission

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get("")
def list_clusters(
    run_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=100),
    user=Depends(require_permission("clusters:read")),
    db: Session = Depends(get_db),
) -> dict:
    return cluster_controller.list_clusters(
        db, run_id=run_id, status=status, page=page, page_size=page_size
    )


@router.get("/{cluster_id}")
def get_cluster(
    cluster_id: str,
    user=Depends(require_permission("clusters:read")),
    db: Session = Depends(get_db),
) -> dict:
    return cluster_controller.get_cluster(db, cluster_id)
