from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import candidate_controller
from src.constants.limits import PAGE_SIZE_DEFAULT
from src.middlewares.rbac import require_permission
from src.schemas.candidates import ReviewRequest

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("")
def list_candidates(
    run_id: str | None = Query(default=None),
    decision: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=PAGE_SIZE_DEFAULT, ge=1, le=100),
    user=Depends(require_permission("candidates:read")),
    db: Session = Depends(get_db),
) -> dict:
    return candidate_controller.list_candidates(
        db, run_id=run_id, decision=decision, status=status, page=page, page_size=page_size
    )


@router.get("/{candidate_id}")
def get_candidate(
    candidate_id: str,
    user=Depends(require_permission("candidates:read")),
    db: Session = Depends(get_db),
) -> dict:
    return candidate_controller.get_candidate(db, candidate_id)


@router.post("/{candidate_id}/review")
def review_candidate(
    candidate_id: str,
    payload: ReviewRequest,
    request: Request,
    user=Depends(require_permission("candidates:review")),
    db: Session = Depends(get_db),
) -> dict:
    return candidate_controller.review_candidate(
        db, candidate_id, action=payload.action, note=payload.note, user=user, request=request
    )
