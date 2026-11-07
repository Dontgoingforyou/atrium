"""Фикстуры и хелперы для тестов portal_collab."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator
from contextlib import asynccontextmanager, contextmanager

from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.main import app
from app.schemas.auth import UserPublic
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_regular, user_portal_user_b

COLLAB_API = "/api/v1/portal"


def assert_api_error(response: Response, status: int, code: str) -> None:
    """Ошибка AppError: и HTTP-статус, и контрактный `code`."""
    assert response.status_code == status, response.text
    assert response.json()["code"] == code


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


@contextmanager
def as_user_regular() -> Iterator[None]:
    with as_user(user_portal_regular):
        yield


@contextmanager
def as_user_b() -> Iterator[None]:
    with as_user(user_portal_user_b):
        yield


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
