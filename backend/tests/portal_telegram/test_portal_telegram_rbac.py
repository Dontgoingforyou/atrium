"""RBAC / 401 / timesheet 403: матрица REST telegram bind."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from tests.portal_telegram.conftest import TELEGRAM_BIND_API, assert_api_error


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", f"{TELEGRAM_BIND_API}/init"),
        ("GET", f"{TELEGRAM_BIND_API}/status"),
        ("DELETE", TELEGRAM_BIND_API),
    ],
)
async def test_telegram_bind_require_auth(
    client_sqlite_only: AsyncClient,
    method: str,
    path: str,
) -> None:
    r = await client_sqlite_only.request(method, path)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", f"{TELEGRAM_BIND_API}/init"),
        ("GET", f"{TELEGRAM_BIND_API}/status"),
        ("DELETE", TELEGRAM_BIND_API),
    ],
)
async def test_telegram_bind_timesheet_forbidden(
    client_developer: AsyncClient,
    method: str,
    path: str,
) -> None:
    r = await client_developer.request(method, path)
    assert_api_error(r, 403, "forbidden")
