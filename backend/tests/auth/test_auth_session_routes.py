"""HTTP `auth_session`: me, logout, logout-beacon."""

from __future__ import annotations

from unittest.mock import AsyncMock

import app.api.v1.routes.auth_session as auth_session_routes
import pytest
from app.core.config import Settings
from httpx import AsyncClient

from tests.auth.cookie_asserts import assert_refresh_cookie_cleared


async def test_me_ok(client_admin: AsyncClient) -> None:
    response = await client_admin.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["sub"] == "admin-sub"
    assert response.json()["is_portal_admin"] is True


async def test_me_unauthorized(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


@pytest.mark.parametrize(
    "header",
    [
        None,
        "Basic dXNlcjpwYXNz",
        "Bearer   ",
    ],
)
async def test_me_rejects_missing_or_non_bearer(
    client_sqlite_only: AsyncClient,
    header: str | None,
) -> None:
    headers = {"Authorization": header} if header is not None else {}
    response = await client_sqlite_only.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert "Bearer" in response.json()["message"]


async def test_logout_without_bearer_does_not_touch_sso(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalidate = AsyncMock()
    logout_sso = AsyncMock()
    monkeypatch.setattr(auth_session_routes.token_cache, "invalidate_token", invalidate)
    monkeypatch.setattr(auth_session_routes, "logout_via_sso", logout_sso)
    r = await client.post("/api/v1/auth/logout")
    assert r.status_code == 204
    invalidate.assert_not_awaited()
    logout_sso.assert_not_awaited()
    assert_refresh_cookie_cleared(r)


async def test_logout_with_bearer_invalidates_cache_and_sso(
    patch_oidc_settings: Settings,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalidate = AsyncMock()
    logout_sso = AsyncMock(return_value=True)
    monkeypatch.setattr(auth_session_routes.token_cache, "invalidate_token", invalidate)
    monkeypatch.setattr(auth_session_routes, "logout_via_sso", logout_sso)
    r = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer access-xyz"},
    )
    assert r.status_code == 204
    invalidate.assert_awaited_once_with("access-xyz")
    logout_sso.assert_awaited_once()
    assert_refresh_cookie_cleared(r)


async def test_logout_empty_bearer_token_is_noop(
    patch_oidc_settings: Settings,
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalidate = AsyncMock()
    monkeypatch.setattr(auth_session_routes.token_cache, "invalidate_token", invalidate)
    r = await client.post("/api/v1/auth/logout", headers={"Authorization": "Bearer   "})
    assert r.status_code == 204
    invalidate.assert_not_awaited()


async def test_logout_beacon_empty_token(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalidate = AsyncMock()
    logout_sso = AsyncMock()
    monkeypatch.setattr(auth_session_routes.token_cache, "invalidate_token", invalidate)
    monkeypatch.setattr(auth_session_routes, "logout_via_sso", logout_sso)
    r = await client.post("/api/v1/auth/logout-beacon", json={"access_token": "  "})
    assert r.status_code == 204
    invalidate.assert_not_awaited()
    logout_sso.assert_not_awaited()


async def test_logout_beacon_rejects_implausible_jwt(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalidate = AsyncMock()
    logout_sso = AsyncMock()
    monkeypatch.setattr(auth_session_routes.token_cache, "invalidate_token", invalidate)
    monkeypatch.setattr(auth_session_routes, "logout_via_sso", logout_sso)
    r = await client.post("/api/v1/auth/logout-beacon", json={"access_token": "not-a-jwt"})
    assert r.status_code == 204
    invalidate.assert_not_awaited()
    logout_sso.assert_not_awaited()


async def test_logout_beacon_invalidates_token_without_sso(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalidate = AsyncMock()
    logout_sso = AsyncMock()
    monkeypatch.setattr(auth_session_routes.token_cache, "invalidate_token", invalidate)
    monkeypatch.setattr(auth_session_routes, "logout_via_sso", logout_sso)
    r = await client.post("/api/v1/auth/logout-beacon", json={"access_token": " header.payload.beacon-tok "})
    assert r.status_code == 204
    invalidate.assert_awaited_once_with("header.payload.beacon-tok")
    logout_sso.assert_not_awaited()


async def test_logout_beacon_token_too_long_422(client: AsyncClient) -> None:
    r = await client.post("/api/v1/auth/logout-beacon", json={"access_token": "a" * 8193})
    assert r.status_code == 422
