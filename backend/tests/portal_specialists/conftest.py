"""Фикстуры для тестов доски воронки специалистов."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.auth_constants import SSO_GID_OUTSTAFF
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.main import app
from app.schemas.auth import UserPublic
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_manager, user_portal_no_idp_groups

SPECIALISTS_API = "/api/v1/portal/specialists"
_AUTH_UUID = "00000000-0000-0000-0000-000000000001"


def assert_api_error(response: Response, status: int, code: str) -> None:
    """Ошибка AppError: и HTTP-статус, и контрактный `code`."""
    assert response.status_code == status, response.text
    assert response.json()["code"] == code


def assert_pydantic_422(response: Response) -> None:
    assert response.status_code == 422, response.text
    assert "detail" in response.json()


@contextmanager
def override_dependency(dependency: object, override: object) -> Iterator[None]:
    """Подменить Depends без `dependency_overrides.clear()`."""
    previous = app.dependency_overrides.get(dependency)
    app.dependency_overrides[dependency] = override
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[dependency] = previous
        else:
            app.dependency_overrides.pop(dependency, None)


@contextmanager
def as_user(user_factory: Callable[[], UserPublic]) -> Iterator[None]:
    """Временно подменить get_current_user без clear()."""
    previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = user_factory
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[get_current_user] = previous
        else:
            app.dependency_overrides.pop(get_current_user, None)


@asynccontextmanager
async def async_client_as(
    session: AsyncSession,
    user_factory: Callable[[], UserPublic],
) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент с сессией и пользователем, без `dependency_overrides.clear()`."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield session

    with override_dependency(get_db_session, _db), as_user(user_factory):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


def user_portal_manager_b() -> UserPublic:
    """Второй менеджер — для проверки IDOR-защиты."""
    return UserPublic(
        sub="manager-b-sub",
        email="mgr_b@example.com",
        username="manager_b",
        full_name="Manager B",
        idp_groups=["outstaff"],
        is_portal_admin=False,
        gid_number=SSO_GID_OUTSTAFF,
    )


def user_specialist() -> UserPublic:
    """Специалист/студент — не имеет доступа к доске."""
    from app.core.auth_constants import IDP_GROUP_DEVELOPER

    return UserPublic(
        sub="specialist-sub",
        email="spec@example.com",
        username="specialist",
        full_name="Specialist User",
        idp_groups=[IDP_GROUP_DEVELOPER],
        is_portal_admin=False,
    )


@pytest.fixture
async def session_with_board(sqlite_session: AsyncSession) -> AsyncSession:
    """SQLite-сессия с тестовыми колонками и записями доски."""
    cols = [
        PortalSpecialistColumn(key="new", title="Новичок", color="#6366f1", position=0, jira_status_id="10001"),
        PortalSpecialistColumn(key="cv_sent", title="Отправили CV", color="#3b82f6", position=1),
        PortalSpecialistColumn(key="hired", title="Принят", color="#22c55e", position=2),
    ]
    sqlite_session.add_all(cols)

    sqlite_session.add(
        PortalUserProfile(
            sub="specialist-sub",
            email="spec@example.com",
            full_name="Specialist User",
            username="specialist",
            portal_chat_allowed=False,
        )
    )
    sqlite_session.add(
        PortalUserProfile(
            sub="manager-b-sub",
            email="mgr_b@example.com",
            full_name="Manager B",
            username="manager_b",
        )
    )
    sqlite_session.add(
        PortalUserProfile(
            sub="purge-target-sub",
            email="purge@example.com",
            full_name="Purge Target",
            username="purge_target",
            portal_chat_allowed=False,
        )
    )

    entry = PortalManagerSpecialist(
        manager_sub="manager-sub",
        specialist_sub="specialist-sub",
        column_key="new",
        position=0,
    )
    sqlite_session.add(entry)

    await sqlite_session.commit()
    return sqlite_session


@pytest.fixture
async def client_sqlite_only_board(
    session_with_board: AsyncSession,
    patch_oidc_settings: Any,
) -> AsyncIterator[AsyncClient]:
    """API с доской, без подмены пользователя (401-матрица)."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield session_with_board

    with override_dependency(get_db_session, _db):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac


@pytest.fixture
async def client_manager(
    session_with_board: AsyncSession,
    patch_oidc_settings: Any,
) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент от имени менеджера."""
    async with async_client_as(session_with_board, user_portal_manager) as ac:
        yield ac


@pytest.fixture
async def client_manager_b(
    session_with_board: AsyncSession,
    patch_oidc_settings: Any,
) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент от имени второго менеджера (для IDOR-проверок)."""
    async with async_client_as(session_with_board, user_portal_manager_b) as ac:
        yield ac


@pytest.fixture
async def client_specialist_user(
    session_with_board: AsyncSession,
    patch_oidc_settings: Any,
) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент от имени специалиста (студента) — доступ запрещён."""
    async with async_client_as(session_with_board, user_specialist) as ac:
        yield ac


@pytest.fixture
async def client_regular_user(
    session_with_board: AsyncSession,
    patch_oidc_settings: Any,
) -> AsyncIterator[AsyncClient]:
    """Авторизованный сотрудник без роли менеджера."""
    async with async_client_as(session_with_board, user_portal_no_idp_groups) as ac:
        yield ac


@pytest.fixture
async def client_admin_board(
    session_with_board: AsyncSession,
    patch_oidc_settings: Any,
) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент от имени администратора с тестовой доской."""
    async with async_client_as(session_with_board, user_portal_admin) as ac:
        yield ac


@pytest.fixture
async def client_developer_board(
    session_with_board: AsyncSession,
    patch_oidc_settings: Any,
) -> AsyncIterator[AsyncClient]:
    """Timesheet-only клиент с тестовой доской (403 NON_DEVELOPER)."""
    from tests.helpers.portal_test_users import user_portal_developer

    async with async_client_as(session_with_board, user_portal_developer) as ac:
        yield ac
