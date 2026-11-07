"""Тесты POST /api/v1/auth/admin-session (сессия SQLAdmin по Bearer портала)."""

from __future__ import annotations

from app.api.deps_auth import get_current_user
from app.main import app
from app.schemas.auth import UserPublic
from httpx import AsyncClient

from tests.helpers.admin_session import decode_admin_session_cookie


def _admin_user() -> UserPublic:
    return UserPublic(
        sub="admin-sub",
        email="a@example.com",
        username="admin",
        full_name="Admin",
        idp_groups=["cosmolet_role_admin"],
        is_portal_admin=True,
    )


def _plain_user() -> UserPublic:
    return UserPublic(
        sub="u1",
        email="u@example.com",
        username="user",
        full_name="User",
        idp_groups=["outstaff"],
        is_portal_admin=False,
    )


async def test_admin_session_redirect_for_portal_admin(client_admin_session: AsyncClient) -> None:
    async def override() -> UserPublic:
        return _admin_user()

    app.dependency_overrides[get_current_user] = override
    try:
        r = await client_admin_session.post(
            "/api/v1/auth/admin-session",
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert r.status_code == 200
    assert r.json() == {"redirect_url": "/admin/"}


async def test_admin_session_stores_email_and_full_name_in_cookie(
    client_admin_session: AsyncClient,
) -> None:
    async def override() -> UserPublic:
        return _admin_user()

    app.dependency_overrides[get_current_user] = override
    try:
        r = await client_admin_session.post(
            "/api/v1/auth/admin-session",
            headers={"Authorization": "Bearer test-token"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert r.status_code == 200
    set_cookie = r.headers.get_list("set-cookie")
    assert set_cookie, "ожидается Set-Cookie с сессией SQLAdmin"
    admin_cookie = next(c for c in set_cookie if c.startswith("admin_session="))
    session_payload = decode_admin_session_cookie(admin_cookie)
    assert session_payload.get("admin_sub") == "admin-sub"
    assert session_payload.get("admin_email") == "a@example.com"
    assert session_payload.get("admin_full_name") == "Admin"


async def test_admin_session_forbidden_for_non_admin(client_admin_session: AsyncClient) -> None:
    async def override() -> UserPublic:
        return _plain_user()

    app.dependency_overrides[get_current_user] = override
    try:
        r = await client_admin_session.post(
            "/api/v1/auth/admin-session",
            headers={"Authorization": "Bearer t"},
            follow_redirects=False,
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert r.status_code == 403


async def test_admin_session_unauthorized_without_bearer(client_admin_session: AsyncClient) -> None:
    r = await client_admin_session.post("/api/v1/auth/admin-session", follow_redirects=False)
    assert r.status_code == 401
    assert r.json()["code"] == "unauthorized"


async def test_admin_session_requires_bearer_prefix(client_admin_session: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = _admin_user
    try:
        r = await client_admin_session.post(
            "/api/v1/auth/admin-session",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert r.status_code == 401
    assert "Bearer" in r.json()["message"]


async def test_admin_session_empty_bearer_token(client_admin_session: AsyncClient) -> None:
    app.dependency_overrides[get_current_user] = _admin_user
    try:
        r = await client_admin_session.post(
            "/api/v1/auth/admin-session",
            headers={"Authorization": "Bearer   "},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
    assert r.status_code == 401
    assert "Требуется заголовок" in r.json()["message"]
