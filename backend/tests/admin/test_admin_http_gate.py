"""HTTP-гейт SQLAdmin: cookie-сессия и сверка is_portal_admin через async_session_factory."""

from __future__ import annotations

from typing import Any

import pytest
from app.admin.auth import KeycloakAdminAuth
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.admin_session import ADMIN_SESSION_COOKIE, encode_admin_session
from tests.helpers.portal_test_users import user_portal_admin


class _ReuseSession:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def __aenter__(self) -> AsyncSession:
        return self._session

    async def __aexit__(self, *args: object) -> None:
        return None


def _patch_admin_auth_factory(monkeypatch: pytest.MonkeyPatch, session: AsyncSession) -> None:
    monkeypatch.setattr(
        "app.infrastructure.db.session.async_session_factory",
        lambda: _ReuseSession(session),
    )


def _admin_cookie(*, sub: str = "admin-sub") -> dict[str, str]:
    return {
        ADMIN_SESSION_COOKIE: encode_admin_session(
            {
                "admin_sub": sub,
                "admin_email": "admin@example.com",
                "admin_full_name": "Admin",
            }
        )
    }


@pytest.mark.asyncio
async def test_admin_index_without_cookie_redirects_to_login(admin_http_client: AsyncClient) -> None:
    r = await admin_http_client.get("/admin/")
    assert r.status_code in {302, 303, 307}
    location = r.headers.get("location", "")
    assert "/admin/login" in location


@pytest.mark.asyncio
async def test_admin_login_page_without_session_is_ok(admin_http_client: AsyncClient) -> None:
    r = await admin_http_client.get("/admin/login")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_index_with_portal_admin_session_ok(
    admin_http_client: AsyncClient,
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_admin_auth_factory(monkeypatch, sqlite_session)
    admin_http_client.cookies.update(_admin_cookie())
    r = await admin_http_client.get("/admin/")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_index_demoted_admin_rejected_and_session_cleared(
    admin_http_client: AsyncClient,
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = await sqlite_session.get(PortalUserProfile, user_portal_admin().sub)
    assert profile is not None
    profile.is_portal_admin = False
    await sqlite_session.commit()

    _patch_admin_auth_factory(monkeypatch, sqlite_session)
    admin_http_client.cookies.update(_admin_cookie())
    r = await admin_http_client.get("/admin/")
    assert r.status_code != 200
    location = r.headers.get("location", "")
    assert "/admin/login" in location or r.status_code in {302, 303, 307}

    r2 = await admin_http_client.get("/admin/")
    assert r2.status_code != 200


@pytest.mark.asyncio
async def test_admin_exit_to_portal_with_session_clears_cookie(
    admin_http_client: AsyncClient,
) -> None:
    admin_http_client.cookies.update(_admin_cookie())
    r = await admin_http_client.post("/admin/exit-to-portal")
    assert r.status_code == 303
    assert r.headers.get("location") == "/"
    set_cookie = ";".join(r.headers.get_list("set-cookie")).lower()
    assert ADMIN_SESSION_COOKIE in set_cookie
    assert "admin_session=null" in set_cookie or "expires=thu, 01 jan 1970" in set_cookie


@pytest.mark.asyncio
async def test_profile_is_portal_admin_missing_profile(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_admin_auth_factory(monkeypatch, sqlite_session)
    auth = KeycloakAdminAuth(secret_key="test-secret")
    assert await auth._profile_is_portal_admin("no-such-sub") is False


@pytest.mark.asyncio
async def test_profile_is_portal_admin_false_flag(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_admin_auth_factory(monkeypatch, sqlite_session)
    auth = KeycloakAdminAuth(secret_key="test-secret")
    assert await auth._profile_is_portal_admin("user-sub") is False
    assert await auth._profile_is_portal_admin(user_portal_admin().sub) is True


@pytest.mark.asyncio
async def test_profile_is_portal_admin_db_error_returns_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Boom:
        async def __aenter__(self) -> Any:
            raise RuntimeError("db down")

        async def __aexit__(self, *args: object) -> None:
            return None

    monkeypatch.setattr("app.infrastructure.db.session.async_session_factory", lambda: _Boom())
    auth = KeycloakAdminAuth(secret_key="test-secret")
    assert await auth._profile_is_portal_admin("admin-sub") is False
