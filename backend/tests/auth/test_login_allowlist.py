"""Белый список входа (PORTAL_LOGIN_ALLOWLIST)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import app.api.v1.routes.auth as auth_routes
import httpx
import pytest
from app.api.deps_auth import verify_access_token
from app.core.config import Settings
from app.core.exceptions import ForbiddenError
from app.schemas.auth import UserPublic
from app.services.sso.login_allowlist import ensure_portal_login_allowed
from httpx import AsyncClient

from tests.conftest import make_oidc_settings

_CALLBACK = "http://localhost:5173/auth/callback"


def _user(*, email: str = "u@example.com") -> UserPublic:
    return UserPublic(
        sub="user-1",
        email=email,
        username="u",
        full_name="",
        idp_groups=[],
        is_portal_admin=False,
    )


def test_empty_allowlist_allows_anyone() -> None:
    s = Settings(database_url="sqlite+aiosqlite:///:memory:", portal_login_allowlist="")
    ensure_portal_login_allowed(_user(email="anyone@example.com"), s)


def test_allowlist_accepts_listed_email_case_insensitive() -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        portal_login_allowlist="  Alpha@Example.com , beta@example.com ",
    )
    ensure_portal_login_allowed(_user(email="alpha@example.com"), s)


def test_allowlist_rejects_unknown_email() -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        portal_login_allowlist="allowed@example.com",
    )
    with pytest.raises(ForbiddenError) as exc:
        ensure_portal_login_allowed(_user(email="other@example.com"), s)
    assert exc.value.status_code == 403
    assert exc.value.message == "Нет доступа"


@pytest.mark.asyncio
async def test_verify_token_forbidden_when_email_not_in_allowlist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        sso_client_id="c",
        sso_client_secret="sec",
        sso_service_url="https://gw.example",
        sso_api_prefix="/api/",
        sso_userinfo_path="me",
        sso_token_path="t",
        sso_refresh_path="r",
        portal_login_allowlist="allowed@example.com",
    )
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)
    monkeypatch.setattr(
        "app.api.deps_auth.token_cache.get_cached_userinfo",
        AsyncMock(
            return_value={
                "sub": "user-1",
                "email": "other@example.com",
                "groups": [],
                "_userinfo_v": 3,
            }
        ),
    )
    monkeypatch.setattr(
        "app.api.deps_auth.build_user_public",
        AsyncMock(return_value=_user(email="other@example.com")),
    )
    db = AsyncMock()
    client = httpx.AsyncClient()
    with pytest.raises(ForbiddenError) as exc:
        await verify_access_token("tok", db, client)
    assert exc.value.message == "Нет доступа"
    await client.aclose()


async def test_token_exchange_forbidden_when_email_not_in_allowlist(
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = make_oidc_settings(portal_login_allowlist="allowed@example.com")
    monkeypatch.setattr(auth_routes, "get_settings", lambda: s)
    monkeypatch.setattr("app.api.deps_auth.get_settings", lambda: s)

    async def _exchange(**_kwargs: object) -> dict[str, str | int]:
        return {"access_token": "dummy", "refresh_token": "r1", "expires_in": 60}

    async def _userinfo(**_kwargs: object) -> dict[str, object]:
        return {
            "sub": "user-1",
            "email": "other@example.com",
            "preferred_username": "u",
            "groups": [],
        }

    monkeypatch.setattr(auth_routes, "exchange_authorization_code", _exchange)
    monkeypatch.setattr(auth_routes, "fetch_user_info_from_gateway", _userinfo)
    response = await client_sqlite_only.post(
        "/api/v1/auth/token",
        json={"code": "code", "redirect_uri": _CALLBACK, "code_verifier": "v" * 43},
    )
    assert response.status_code == 403
    assert response.json()["message"] == "Нет доступа"
    assert "set-cookie" not in {k.lower() for k in response.headers}


async def test_password_login_forbidden_when_email_not_in_allowlist(
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = make_oidc_settings(portal_login_allowlist="allowed@example.com")
    monkeypatch.setattr(auth_routes, "get_settings", lambda: s)

    async def fake_login(**_kwargs: object) -> tuple[int, dict[str, object]]:
        return 200, {
            "access_token": "access-from-login",
            "refresh_token": "refresh-from-login",
            "expires_in": 120,
            "user": {
                "email": "other@example.com",
                "username": "u",
                "full_name": "User One",
                "groups": [],
                "keycloak_id": "kc-1",
            },
        }

    monkeypatch.setattr(auth_routes, "login_with_password", fake_login)
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": "secret", "redirect_uri": _CALLBACK},
    )
    assert response.status_code == 403
    assert response.json()["message"] == "Нет доступа"
    assert "set-cookie" not in {k.lower() for k in response.headers}
