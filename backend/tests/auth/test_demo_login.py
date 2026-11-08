"""Локальный вход демо-учётками без SSO."""

from __future__ import annotations

import pytest
from app.services.demo_accounts import (
    DemoTokenInvalid,
    authenticate_demo,
    demo_signing_secret,
    issue_demo_tokens,
    read_demo_access_claims,
)
from httpx import AsyncClient

from tests.auth.cookie_asserts import refresh_set_cookie
from tests.conftest import make_oidc_settings


def test_authenticate_demo_accepts_username_and_rejects_password() -> None:
    account = authenticate_demo("admin", "demo-admin")
    assert account is not None
    assert account.email == "demo-admin@example.com"
    assert authenticate_demo("demo-admin@example.com", "demo-admin") is not None
    assert authenticate_demo("admin", "wrong") is None
    assert authenticate_demo("nobody", "demo-admin") is None


def test_demo_token_rejects_bad_signature() -> None:
    settings = make_oidc_settings()
    account = authenticate_demo("user", "demo-user")
    assert account is not None
    access, _refresh, _ttl, _claims = issue_demo_tokens(account, demo_signing_secret(settings))
    with pytest.raises(DemoTokenInvalid):
        read_demo_access_claims(access + "x", demo_signing_secret(settings))


async def test_demo_login_without_sso_and_me(
    client_sqlite_only: AsyncClient,
) -> None:
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "manager", "password": "demo-manager"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "demo-manager@example.com"
    assert body["user"]["full_name"] == "Иван Петров"
    assert body["user"]["gid_number"] == "10000"
    assert body["user"]["is_portal_admin"] is False
    assert body["oauth_client_id"] == "atrium-demo"
    assert "httponly" in refresh_set_cookie(response).lower()

    me = await client_sqlite_only.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "manager"


async def test_demo_admin_login(client_sqlite_only: AsyncClient) -> None:
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "demo-admin@example.com", "password": "demo-admin"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["is_portal_admin"] is True


async def test_demo_wrong_password_does_not_call_sso(
    client_sqlite_only: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _boom(**_kwargs: object) -> None:
        raise AssertionError("SSO не должен вызываться для известной демо-учётки")

    monkeypatch.setattr("app.api.v1.routes.auth.login_with_password", _boom)
    response = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "user", "password": "nope"},
    )
    assert response.status_code == 401


async def test_demo_refresh(client_sqlite_only: AsyncClient) -> None:
    login = await client_sqlite_only.post(
        "/api/v1/auth/login",
        json={"email": "manager", "password": "demo-manager"},
    )
    assert login.status_code == 200
    raw_cookie = refresh_set_cookie(login)
    token_cookie = raw_cookie.split(";", 1)[0]
    refreshed = await client_sqlite_only.post(
        "/api/v1/auth/refresh",
        json={},
        headers={"cookie": token_cookie},
    )
    assert refreshed.status_code == 200
    token = refreshed.json()["access_token"]
    me = await client_sqlite_only.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "demo-manager@example.com"


async def test_unknown_login_still_requires_sso(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import Settings

    s = Settings(database_url="sqlite+aiosqlite:///:memory:", sso_service_url="")
    monkeypatch.setattr("app.api.v1.routes.auth.get_settings", lambda: s)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "u@example.com", "password": "secret"},
    )
    assert response.status_code == 503
