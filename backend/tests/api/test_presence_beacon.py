"""POST /portal/users/me/presence-beacon."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from app.schemas.auth import UserPublic
from httpx import AsyncClient


def _make_user(sub: str = "beacon-user-sub") -> UserPublic:
    return UserPublic(
        sub=sub,
        email="beacon@example.com",
        username="beacon",
        full_name="Beacon User",
        idp_groups=[],
        is_portal_admin=False,
    )


@pytest.mark.asyncio
async def test_presence_beacon_returns_204_for_invalid_jwt(client_sqlite_only: AsyncClient) -> None:
    with patch("app.api.v1.routes.portal_users.record_presence") as mock_rec:
        resp = await client_sqlite_only.post(
            "/api/v1/portal/users/me/presence-beacon",
            json={"access_token": "not-a-jwt", "visible": False, "active": False},
        )
    assert resp.status_code == 204
    mock_rec.assert_not_called()


@pytest.mark.asyncio
async def test_presence_beacon_returns_204_for_garbage_token(client_sqlite_only: AsyncClient) -> None:
    with patch("app.api.v1.routes.portal_users.record_presence") as mock_rec:
        resp = await client_sqlite_only.post(
            "/api/v1/portal/users/me/presence-beacon",
            json={"access_token": "", "visible": False, "active": False},
        )
    assert resp.status_code == 204
    mock_rec.assert_not_called()


@pytest.mark.asyncio
async def test_presence_beacon_returns_204_when_verify_fails(client_sqlite_only: AsyncClient) -> None:
    from fastapi import HTTPException

    with (
        patch(
            "app.api.v1.routes.portal_users.verify_access_token",
            new=AsyncMock(side_effect=HTTPException(status_code=401, detail="bad")),
        ),
        patch("app.api.v1.routes.portal_users.record_presence") as mock_rec,
    ):
        resp = await client_sqlite_only.post(
            "/api/v1/portal/users/me/presence-beacon",
            json={"access_token": "aaaa.bbbb.cccc", "visible": False, "active": False},
        )
    assert resp.status_code == 204
    mock_rec.assert_not_called()


@pytest.mark.asyncio
async def test_presence_beacon_records_presence_on_valid_token(client_sqlite_only: AsyncClient) -> None:
    user = _make_user()
    with (
        patch(
            "app.api.v1.routes.portal_users.verify_access_token",
            new=AsyncMock(return_value=user),
        ),
        patch("app.api.v1.routes.portal_users.record_presence", new=AsyncMock()) as mock_rec,
        patch("app.api.v1.routes.portal_users.set_last_seen_iso_now", new=AsyncMock()) as mock_iso,
        patch("app.api.v1.routes.portal_users.finalize_last_seen_in_db", new=AsyncMock()) as mock_finalize,
    ):
        resp = await client_sqlite_only.post(
            "/api/v1/portal/users/me/presence-beacon",
            json={"access_token": "aaaa.bbbb.cccc", "visible": False, "active": False},
        )
    assert resp.status_code == 204
    mock_rec.assert_awaited_once_with(user_sub=user.sub, visible=False, active=False)
    mock_iso.assert_awaited_once_with(user_sub=user.sub)
    mock_finalize.assert_awaited_once()


@pytest.mark.asyncio
async def test_presence_beacon_accepts_visible_true(client_sqlite_only: AsyncClient) -> None:
    user = _make_user()
    with (
        patch(
            "app.api.v1.routes.portal_users.verify_access_token",
            new=AsyncMock(return_value=user),
        ),
        patch("app.api.v1.routes.portal_users.record_presence", new=AsyncMock()) as mock_rec,
    ):
        resp = await client_sqlite_only.post(
            "/api/v1/portal/users/me/presence-beacon",
            json={"access_token": "aaaa.bbbb.cccc", "visible": True, "active": True},
        )
    assert resp.status_code == 204
    mock_rec.assert_awaited_once_with(user_sub=user.sub, visible=True, active=True)


@pytest.mark.asyncio
async def test_presence_beacon_real_verify_mocks_only_sso(client_sqlite_only: AsyncClient) -> None:
    """verify_access_token выполняется; мок только SSO userinfo."""
    payload = {
        "sub": "user-sub",
        "email": "user@example.com",
        "preferred_username": "user",
        "name": "User",
        "groups": ["outstaff"],
    }
    with (
        patch("app.api.deps_auth.token_cache.get_cached_userinfo", new=AsyncMock(return_value=None)),
        patch("app.api.deps_auth.token_cache.set_cached_userinfo", new=AsyncMock()),
        patch(
            "app.api.deps_auth.fetch_user_info_from_gateway",
            new=AsyncMock(return_value=payload),
        ),
        patch("app.api.v1.routes.portal_users.record_presence", new=AsyncMock()) as mock_rec,
        patch("app.api.v1.routes.portal_users.set_last_seen_iso_now", new=AsyncMock()),
        patch("app.api.v1.routes.portal_users.finalize_last_seen_in_db", new=AsyncMock()),
    ):
        resp = await client_sqlite_only.post(
            "/api/v1/portal/users/me/presence-beacon",
            json={"access_token": "aaaa.bbbb.cccc", "visible": False, "active": False},
        )
    assert resp.status_code == 204
    mock_rec.assert_awaited()
