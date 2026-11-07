"""Фикстуры и хелперы для тестов portal_favorites."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from app.api.deps_auth import get_current_user
from app.main import app
from app.schemas.auth import UserPublic
from httpx import Response

from tests.helpers.portal_test_users import user_portal_regular, user_portal_user_b

FAV_API = "/api/v1/portal/favorites"


def assert_api_error(response: Response, status: int, code: str) -> None:
    """Ошибка AppError: и HTTP-статус, и контрактный `code`."""
    assert response.status_code == status, response.text
    assert response.json()["code"] == code


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


@contextmanager
def as_user_regular() -> Iterator[None]:
    with as_user(user_portal_regular):
        yield


@contextmanager
def as_user_b() -> Iterator[None]:
    with as_user(user_portal_user_b):
        yield
