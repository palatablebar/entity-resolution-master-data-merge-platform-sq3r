from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.config.database import get_db
from src.controllers import auth_controller
from src.middlewares.auth import get_current_user
from src.constants.roles import role_can

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(request: Request, payload: auth_controller.LoginRequest, db: Session = Depends(get_db)) -> dict:
    return auth_controller.login(request, payload, db)


@router.post("/refresh")
def refresh(payload: auth_controller.RefreshRequest, db: Session = Depends(get_db)) -> dict:
    return auth_controller.refresh(payload, db)


@router.get("/me")
def me(user=Depends(get_current_user)) -> dict:
    return auth_controller.me(user)


@router.get("/users")
def list_users(user=Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    from src.constants import error_codes as codes
    from src.utils.errors import AppError

    if not role_can(user.role, "users:admin"):
        raise AppError(codes.FORBIDDEN, "当前角色无权查看用户清单", f"role={user.role}")
    return auth_controller.list_users(db)
