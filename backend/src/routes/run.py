from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import run_controller
from src.constants.limits import PAGE_SIZE_DEFAULT
from src.middlewares.rate_limit import rate_limit
from src.middlewares.rbac import require_permission
from src.schemas.runs import RunCreateRequest

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
def list_runs(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=100),
    user=Depends(require_permission("runs:read")),
    db: Session = Depends(get_db),
) -> dict:
    return run_controller.list_runs(db, status=status, page=page, page_size=page_size)


@router.get("/{run_id}")
def get_run(
    run_id: str,
    user=Depends(require_permission("runs:read")),
    db: Session = Depends(get_db),
) -> dict:
    return run_controller.get_run(db, run_id)


@router.post("")
def create_run(
    payload: RunCreateRequest,
    request: Request,
    user=Depends(require_permission("runs:trigger")),
    db: Session = Depends(get_db),
    _rate: None = rate_limit("runs"),
) -> dict:
    return run_controller.create_run(db, payload, user=user, request=request)


@router.post("/{run_id}/rerun")
def rerun(
    run_id: str,
    request: Request,
    user=Depends(require_permission("runs:trigger")),
    db: Session = Depends(get_db),
    _rate: None = rate_limit("runs"),
) -> dict:
    return run_controller.rerun(db, run_id, user=user, request=request)
