"""RBAC 权限定义与校验。

角色用于分组，细粒度操作使用 permission 字符串，后端逐请求校验。
前端路由守卫/按钮隐藏不作为安全边界。
"""

from __future__ import annotations

from enum import StrEnum


class Role(StrEnum):
    GUEST = "guest"
    MEMBER = "member"
    PHOTOGRAPHER = "photographer"
    MODERATOR = "moderator"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# 细粒度权限点（示意，按业务逐步扩展）
PERMISSIONS = {
    "gallery.image.upload": {Role.PHOTOGRAPHER, Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN},
    "gallery.image.upload.public": {Role.PHOTOGRAPHER, Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN},
    "gallery.image.publish": {Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN},
    "gallery.image.delete.any": {Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN},
    "profile.image.read.own": {Role.MEMBER, Role.PHOTOGRAPHER, Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN},
    "profile.image.upload": {Role.MEMBER, Role.PHOTOGRAPHER, Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN},
    "schedule.use": {Role.MEMBER, Role.PHOTOGRAPHER, Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN},
    "event.manage": {Role.ADMIN, Role.SUPER_ADMIN},
    "event.register": {Role.MEMBER, Role.PHOTOGRAPHER, Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN},
    "page.publish": {Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN},
    "site_config.manage": {Role.ADMIN, Role.SUPER_ADMIN},
    "user.approve": {Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN},
    "audit_log.read": {Role.MODERATOR, Role.ADMIN, Role.SUPER_ADMIN},
}

# 角色继承链：从低到高
_ROLE_LEVEL = {
    Role.GUEST: 0,
    Role.MEMBER: 1,
    Role.PHOTOGRAPHER: 2,
    Role.MODERATOR: 3,
    Role.ADMIN: 4,
    Role.SUPER_ADMIN: 5,
}


def role_level(role: str | Role) -> int:
    try:
        return _ROLE_LEVEL[Role(role)]
    except ValueError:
        return -1


def has_permission(role: str | Role, permission: str) -> bool:
    """判断某角色是否拥有某权限（含更高级角色继承）。"""
    allowed = PERMISSIONS.get(permission)
    if allowed is None:
        return False
    base = role_level(role)
    return any(base >= role_level(r) for r in allowed)


def require_permission(role: str | Role, permission: str) -> None:
    """校验权限，不通过则抛出 PermissionError。"""
    if not has_permission(role, permission):
        raise PermissionError(f"缺少权限: {permission}")