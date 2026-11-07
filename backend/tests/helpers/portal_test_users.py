"""Типовые UserPublic для интеграционных тестов API (импорт из conftest и тестовых модулей)."""

from __future__ import annotations

from app.core.auth_constants import (
    IDP_GROUP_DEVELOPER,
    IDP_GROUP_MANAGER,
    IDP_GROUP_PORTAL_ADMIN,
    SSO_GID_OUTSTAFF,
)
from app.schemas.auth import UserPublic


def user_portal_admin() -> UserPublic:
    return UserPublic(
        sub="admin-sub",
        email="admin@example.com",
        username="admin",
        full_name="Admin",
        idp_groups=[IDP_GROUP_PORTAL_ADMIN],
        is_portal_admin=True,
    )


def user_portal_regular() -> UserPublic:
    return UserPublic(
        sub="user-sub",
        email="user@example.com",
        username="user",
        full_name="User",
        idp_groups=["outstaff"],
        is_portal_admin=False,
        gid_number=SSO_GID_OUTSTAFF,
    )


def user_portal_no_idp_groups() -> UserPublic:
    """Авторизован, но без групп Keycloak из токена (сценарии «нет outstaff / не руководитель»)."""
    return UserPublic(
        sub="user-no-idp",
        email="noidp@example.com",
        username="noidp",
        full_name="No Idp",
        idp_groups=[],
        is_portal_admin=False,
    )


def user_portal_user_b() -> UserPublic:
    return UserPublic(
        sub="user-b",
        email="b@example.com",
        username="ub",
        full_name="User B",
        idp_groups=["outstaff"],
        is_portal_admin=False,
        gid_number=SSO_GID_OUTSTAFF,
    )


def user_portal_procurement() -> UserPublic:
    return UserPublic(
        sub="procurement-sub",
        email="proc@example.com",
        username="procurement",
        full_name="Procurement User",
        idp_groups=["outstaff"],
        is_portal_admin=False,
        gid_number=SSO_GID_OUTSTAFF,
    )


def user_portal_manager() -> UserPublic:
    return UserPublic(
        sub="manager-sub",
        email="mgr@example.com",
        username="manager",
        full_name="Manager",
        idp_groups=["outstaff"],
        is_portal_admin=False,
        gid_number=SSO_GID_OUTSTAFF,
    )


def user_portal_developer() -> UserPublic:
    """Пользователь с ролью «Разработчик» (Keycloak-группа «students»): доступ только к своему ТШ."""
    return UserPublic(
        sub="dev-sub",
        email="dev@example.com",
        username="developer",
        full_name="Developer",
        idp_groups=[IDP_GROUP_DEVELOPER],
        is_portal_admin=False,
        position="student",
    )


def user_au_specialist_with_outstaff() -> UserPublic:
    """Специалист АУ с автоматически выданной группой outstaff — только таймшиты."""
    return UserPublic(
        sub="au-spec-sub",
        email="au.spec@example.com",
        username="au.spec",
        full_name="AU Specialist",
        idp_groups=[IDP_GROUP_DEVELOPER, IDP_GROUP_MANAGER],
        is_portal_admin=False,
        position="au_specialist",
        gid_number=SSO_GID_OUTSTAFF,
    )


def user_manager_students_outstaff() -> UserPublic:
    """Менеджер АУ: students + outstaff и должность руководителя — полный доступ."""
    return UserPublic(
        sub="au-mgr-sub",
        email="au.mgr@example.com",
        username="au.mgr",
        full_name="AU Manager",
        idp_groups=[IDP_GROUP_DEVELOPER, IDP_GROUP_MANAGER],
        is_portal_admin=False,
        position="au_chief",
        gid_number=SSO_GID_OUTSTAFF,
    )


def user_outstaff_not_manager() -> UserPublic:
    """Группа outstaff в IdP, но без gid_number Аутстаффа — не менеджер."""
    return UserPublic(
        sub="outstaff-plain-sub",
        email="outstaff.plain@example.com",
        username="outstaff.plain",
        full_name="Outstaff Plain",
        idp_groups=["outstaff"],
        is_portal_admin=False,
    )
