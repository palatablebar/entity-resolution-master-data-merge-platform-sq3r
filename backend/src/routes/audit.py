from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import audit_controller
from src.middlewares.rbac import require_permission

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs")
def list_logs(
    limit: int = Query(default=50, ge=1, le=200),
    entity_type: str | None = Query(default=None),
    user=Depends(require_permission("audit:read")),
    db: Session = Depends(get_db),
) -> dict:
    return audit_controller.list_logs(db, limit=limit, entity_type=entity_type)
