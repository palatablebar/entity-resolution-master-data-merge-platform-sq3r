from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import meta_controller
from src.middlewares.auth import get_current_user

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/overview")
def overview(user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return meta_controller.overview(db)
