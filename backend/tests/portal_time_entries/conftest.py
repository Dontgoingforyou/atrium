"""Фикстуры для тестов модуля portal_time_entries."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import contextmanager
from datetime import date

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.infrastructure.db.models.portal_time_entry import PortalTimeEntry
from app.main import app
from app.schemas.auth import UserPublic
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_portal_admin,
    user_portal_developer,
    user_portal_manager,
    user_portal_regular,
)

TIME_ENTRIES_API = "/api/v1/portal/time-entries"


def assert_api_error(response: Response, status: int, code: str) -> None:
    """Ошибка AppError: и HTTP-статус, и контрактный `code`."""
    assert response.status_code == status, response.text
    assert response.json()["code"] == code


def assert_pydantic_422(response: Response) -> None:
    assert response.status_code == 422, response.text
    assert "detail" in response.json()


@contextmanager
def override_dependency(
    dependency: object,
    override: object,
) -> Iterator[None]:
    """Подменить Depends без clear()."""
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


@pytest.fixture
async def session_with_entries(sqlite_session: AsyncSession) -> AsyncSession:
    """SQLite-сессия с тестовыми записями таймшита."""
    entries = [
        PortalTimeEntry(
            user_sub="manager-sub",
            worked_on=date(2026, 4, 1),
            minutes=120,
            note="Работа по задаче A",
            task_name="Задача A",
        ),
        PortalTimeEntry(
            user_sub="manager-sub",
            worked_on=date(2026, 4, 15),
            minutes=90,
            note="Код-ревью",
        ),
        PortalTimeEntry(
            user_sub="user-sub",
            worked_on=date(2026, 4, 3),
            minutes=60,
            note="Разработка",
        ),
    ]
    sqlite_session.add_all(entries)
    await sqlite_session.commit()
    return sqlite_session


async def _client_with_user(
    session: AsyncSession,
    user_factory: Callable[[], UserPublic],
) -> AsyncIterator[AsyncClient]:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield session

    prev_db = app.dependency_overrides.get(get_db_session)
    prev_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_factory
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        if prev_db is not None:
            app.dependency_overrides[get_db_session] = prev_db
        else:
            app.dependency_overrides.pop(get_db_session, None)
        if prev_user is not None:
            app.dependency_overrides[get_current_user] = prev_user
        else:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def client_manager_entries(
    session_with_entries: AsyncSession,
    patch_oidc_settings: object,
) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент от имени менеджера с тестовыми записями."""
    async for ac in _client_with_user(session_with_entries, user_portal_manager):
        yield ac


@pytest.fixture
async def client_admin_entries(
    session_with_entries: AsyncSession,
    patch_oidc_settings: object,
) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент от имени администратора с тестовыми записями."""
    async for ac in _client_with_user(session_with_entries, user_portal_admin):
        yield ac


@pytest.fixture
async def client_developer_entries(
    session_with_entries: AsyncSession,
    patch_oidc_settings: object,
) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент от имени developer (только свои записи)."""
    async for ac in _client_with_user(session_with_entries, user_portal_developer):
        yield ac


@pytest.fixture
async def client_regular_entries(
    session_with_entries: AsyncSession,
    patch_oidc_settings: object,
) -> AsyncIterator[AsyncClient]:
    """HTTP-клиент от имени обычного пользователя (outstaff) с записями."""
    async for ac in _client_with_user(session_with_entries, user_portal_regular):
        yield ac
