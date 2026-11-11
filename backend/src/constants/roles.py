"""RBAC 角色与能力矩阵（前后端一致）。"""
from __future__ import annotations

ROLE_ADMIN = "admin"
ROLE_CURATOR = "curator"
ROLE_MARKETING = "marketing"

ALL_ROLES: tuple[str, ...] = (ROLE_ADMIN, ROLE_CURATOR, ROLE_MARKETING)

PERMISSIONS: dict[str, tuple[str, ...]] = {
    "records:read": ALL_ROLES,
    "candidates:read": ALL_ROLES,
    "candidates:review": (ROLE_ADMIN, ROLE_CURATOR),
    "clusters:read": ALL_ROLES,
    "golden:read": ALL_ROLES,
    "golden:export": ALL_ROLES,
    "rules:read": ALL_ROLES,
    "rules:write": (ROLE_ADMIN,),
    "runs:read": ALL_ROLES,
    "runs:trigger": (ROLE_ADMIN, ROLE_CURATOR),
    "audit:read": (ROLE_ADMIN,),
}

ROLE_LABELS = {
    ROLE_ADMIN: "主数据管理员",
    ROLE_CURATOR: "数据管家",
    ROLE_MARKETING: "营销运营（只读）",
}


def role_can(role: str, action: str) -> bool:
    return role in PERMISSIONS.get(action, ())
