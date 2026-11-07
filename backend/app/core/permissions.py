"""Предикаты и хелперы проверки ролей (RBAC).

Единственный источник правды для политики «менеджер или администратор».
"""

from __future__ import annotations

from app.core.auth_constants import (
    IDP_GROUP_DEVELOPER,
    SSO_GID_OUTSTAFF,
    TIMESHEET_ONLY_POSITIONS,
    normalize_sso_gid_number,
)
from app.core.exceptions import ForbiddenError
from app.schemas.auth import UserPublic


def is_manager_or_admin(user: UserPublic) -> bool:
    """Вернуть True, если пользователь — менеджер АУ или администратор портала.

    Менеджер: основной отдел SSO «Аутстафф» (``gid_number == 10000``).
    Группа Keycloak ``outstaff`` сама по себе менеджера не даёт.
    Должности «только таймшиты» отменяют менеджерский доступ.
    """
    if user.is_portal_admin:
        return True
    if user.position in TIMESHEET_ONLY_POSITIONS:
        return False
    return normalize_sso_gid_number(user.gid_number) == SSO_GID_OUTSTAFF


def is_timesheet_only(user: UserPublic) -> bool:
    """Доступ только к таймшитам: по должности SSO или legacy students без менеджера."""
    if user.is_portal_admin:
        return False
    if user.position in TIMESHEET_ONLY_POSITIONS:
        return True
    return IDP_GROUP_DEVELOPER in user.idp_groups and not is_manager_or_admin(user)


def require_manager_or_admin(user: UserPublic, detail: str | None = None) -> None:
    """Проверить роль; бросить ForbiddenError, если пользователь не менеджер и не администратор.

    Args:
        user: текущий пользователь.
        detail: сообщение ошибки; если не передано — используется общее.
    """
    if not is_manager_or_admin(user):
        raise ForbiddenError(detail or "Доступ только для менеджера или администратора портала")
