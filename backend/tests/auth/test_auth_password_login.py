"""Тесты POST /auth/login (password proxy к SSO)."""

from __future__ import annotations

from unittest.mock import MagicMock

import app.api.v1.routes.auth as auth_routes
import httpx
import pytest
from app.core.config import Settings
from app.services.sso.client_resolver import SsoCredentialsNotFoundError
from httpx import AsyncClient

from tests.auth.cookie_asserts import assert_refresh_cookie_set
from tests.conftest import make_oidc_settings

_CALLBACK = "http://localhost:5173/auth/callback"


async def test_password_login_sso_disabled(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import Settings

    s = Settings(database_url="sqlite+aiosqlite:///:memory:", sso_service_url="")
    monkeypatch.setattr(auth_routes, "get_settings", lambda: s)
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "u@example.com",
            "password": "secret",
            "redirect_uri": "http://localhost:5173/auth/callback",
        },
    )
    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


async def test_password_login_bad_redirect(patch_oidc_settings, client_sqlite_only: AsyncClient) -> None:
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={
            "email": "u@example.com",
            "password": "secret",
            "redirect_uri": "https://evil.example/cb",
        },
    )
    assert response.status_code == 400
    assert "redirect_uri" in response.json()["message"]


async def test_password_login_invalid_credentials(
    patch_oidc_settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_login(**_kwargs: object) -> tuple[int, dict[str, object] | None]:
        return 401, None

    monkeypatch.setattr(auth_routes, "login_with_password", fake_login)

    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={
            "email": "u@example.com",
            "password": "wrong",
            "redirect_uri": "http://localhost:5173/auth/callback",
        },
    )
    assert response.status_code == 401
    assert "Неверный email или пароль" in response.json()["message"]


async def test_password_login_sso_unavailable(
    patch_oidc_settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_login(**_kwargs: object) -> tuple[int, dict[str, object] | None]:
        raise httpx.RequestError("connection failed")

    monkeypatch.setattr(auth_routes, "login_with_password", fake_login)

    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={
            "email": "u@example.com",
            "password": "secret",
            "redirect_uri": "http://localhost:5173/auth/callback",
        },
    )
    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


async def test_password_login_success_without_keycloak_id(
    patch_oidc_settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_login(**_kwargs: object) -> tuple[int, dict[str, object]]:
        return 200, {
            "access_token": "access-from-login",
            "refresh_token": "refresh-from-login",
            "expires_in": 120,
            "user": {
                "email": "u@example.com",
                "username": "u",
                "full_name": "User One",
                "groups": ["outstaff"],
                "sub": "sso-sub-1",
                "position": "dev",
            },
        }

    monkeypatch.setattr(auth_routes, "login_with_password", fake_login)

    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={
            "email": "u@example.com",
            "password": "secret",
            "redirect_uri": "http://localhost:5173/auth/callback",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["sub"] == "sso-sub-1"


async def test_password_login_success(
    patch_oidc_settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_login(**_kwargs: object) -> tuple[int, dict[str, object]]:
        return 200, {
            "access_token": "access-from-login",
            "refresh_token": "refresh-from-login",
            "expires_in": 120,
            "user": {
                "email": "u@example.com",
                "username": "u",
                "full_name": "User One",
                "groups": ["outstaff"],
                "keycloak_id": "kc-1",
                "position": "dev",
            },
        }

    monkeypatch.setattr(auth_routes, "login_with_password", fake_login)

    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={
            "email": "u@example.com",
            "password": "secret",
            "redirect_uri": "http://localhost:5173/auth/callback",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"] == "access-from-login"
    assert data["refresh_token"] is None
    assert data["user"]["sub"] == "kc-1"
    assert data["user"]["email"] == "u@example.com"
    assert data["oauth_client_id"] == "test-client"
    assert_refresh_cookie_set(response, value="refresh-from-login")


async def test_password_login_default_redirect_when_single_uri(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_login(**_kwargs: object) -> tuple[int, dict[str, object]]:
        return 200, {
            "access_token": "at",
            "refresh_token": "rt",
            "expires_in": 60,
            "user": {"sub": "u-1", "email": "u@example.com", "username": "u"},
        }

    monkeypatch.setattr(auth_routes, "login_with_password", fake_login)
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "u@example.com", "password": "secret"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["sub"] == "u-1"


async def test_password_login_requires_redirect_when_multiple_uris(
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = make_oidc_settings(
        sso_allowed_redirect_uris=f"{_CALLBACK},http://localhost:9088/auth/callback",
    )
    monkeypatch.setattr(auth_routes, "get_settings", lambda: s)
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "u@example.com", "password": "secret"},
    )
    assert response.status_code == 400
    assert "redirect_uri" in response.json()["message"]


async def test_password_login_sso_non_401_is_503(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_login(**_kwargs: object) -> tuple[int, dict[str, object] | None]:
        return 500, None

    monkeypatch.setattr(auth_routes, "login_with_password", fake_login)
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "u@example.com", "password": "secret", "redirect_uri": _CALLBACK},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


async def test_password_login_no_sso_credentials(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        auth_routes,
        "resolve_sso_credentials_for_redirect",
        MagicMock(side_effect=SsoCredentialsNotFoundError("uri")),
    )
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "u@example.com", "password": "secret", "redirect_uri": _CALLBACK},
    )
    assert response.status_code == 400
    assert "Внешний вход не настроен" in response.json()["message"]


async def test_password_login_userinfo_network_error(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_login(**_kwargs: object) -> tuple[int, dict[str, object]]:
        return 200, {"access_token": "at", "expires_in": 60, "user": {"email": "u@example.com"}}

    async def _userinfo_fail(**_kwargs: object) -> None:
        raise httpx.ConnectError("down")

    monkeypatch.setattr(auth_routes, "login_with_password", fake_login)
    monkeypatch.setattr(auth_routes, "resolve_gateway_payload_after_password_login", _userinfo_fail)
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "u@example.com", "password": "secret", "redirect_uri": _CALLBACK},
    )
    assert response.status_code == 503
    assert response.json()["code"] == "service_unavailable"


async def test_password_login_empty_profile_is_401(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_login(**_kwargs: object) -> tuple[int, dict[str, object]]:
        return 200, {"access_token": "at", "expires_in": 60}

    async def _empty(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(auth_routes, "login_with_password", fake_login)
    monkeypatch.setattr(auth_routes, "resolve_gateway_payload_after_password_login", _empty)
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "u@example.com", "password": "secret", "redirect_uri": _CALLBACK},
    )
    assert response.status_code == 401
    assert "профиль" in response.json()["message"]


async def test_password_login_email_too_long_422(
    patch_oidc_settings: Settings,
    client_sqlite_only: AsyncClient,
) -> None:
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "a" * 256, "password": "secret", "redirect_uri": _CALLBACK},
    )
    assert response.status_code == 422
