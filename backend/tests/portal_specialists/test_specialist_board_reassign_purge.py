"""Смена менеджера и удаление специалиста из портала."""

from __future__ import annotations

import pytest
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin
from tests.portal_specialists.conftest import assert_api_error


@pytest.mark.asyncio
async def test_reassign_manager_admin(client_admin_board: AsyncClient) -> None:
    res = await client_admin_board.post(
        "/api/v1/portal/specialists/board/specialist-sub/reassign-manager",
        json={
            "from_manager_sub": "manager-sub",
            "to_manager_sub": "manager-b-sub",
        },
    )
    assert res.status_code == 204
    listed = await client_admin_board.get(
        "/api/v1/portal/specialists/board/by-specialist?specialist_sub=specialist-sub",
    )
    assert listed.status_code == 200
    subs = {row["manager_sub"] for row in listed.json()}
    assert "manager-b-sub" in subs
    assert "manager-sub" not in subs
    await client_admin_board.post(
        "/api/v1/portal/specialists/board/specialist-sub/reassign-manager",
        json={
            "from_manager_sub": "manager-b-sub",
            "to_manager_sub": "manager-sub",
        },
    )


@pytest.mark.asyncio
async def test_reassign_manager_forbidden_for_manager(client_manager: AsyncClient) -> None:
    res = await client_manager.post(
        "/api/v1/portal/specialists/board/specialist-sub/reassign-manager",
        json={
            "from_manager_sub": "manager-sub",
            "to_manager_sub": "manager-b-sub",
        },
    )
    assert_api_error(res, 403, "forbidden")


@pytest.mark.asyncio
async def test_reassign_manager_unknown_from_manager_404(client_admin_board: AsyncClient) -> None:
    res = await client_admin_board.post(
        "/api/v1/portal/specialists/board/specialist-sub/reassign-manager",
        json={
            "from_manager_sub": "ghost-manager-sub",
            "to_manager_sub": "manager-b-sub",
        },
    )
    assert_api_error(res, 404, "not_found")


@pytest.mark.asyncio
async def test_by_specialist_forbidden_for_manager(client_manager: AsyncClient) -> None:
    res = await client_manager.get(
        "/api/v1/portal/specialists/board/by-specialist",
        params={"specialist_sub": "specialist-sub"},
    )
    assert_api_error(res, 403, "forbidden")


@pytest.mark.asyncio
async def test_purge_specialist_forbidden_for_manager(client_manager: AsyncClient) -> None:
    res = await client_manager.delete("/api/v1/portal/specialists/purge-target-sub")
    assert_api_error(res, 403, "forbidden")


@pytest.mark.asyncio
async def test_purge_specialist_admin(client_admin_board: AsyncClient) -> None:
    res = await client_admin_board.delete("/api/v1/portal/specialists/purge-target-sub")
    assert res.status_code == 204
    profile = await client_admin_board.get("/api/v1/portal/specialists/purge-target-sub/profile")
    assert_api_error(profile, 404, "not_found")


@pytest.mark.asyncio
async def test_purge_specialist_self_forbidden(client_admin_board: AsyncClient) -> None:
    res = await client_admin_board.delete("/api/v1/portal/specialists/manager-sub")
    assert_api_error(res, 403, "forbidden")


@pytest.mark.asyncio
async def test_purge_specialist_chat_user_forbidden(
    client_admin_board: AsyncClient,
    session_with_board: AsyncSession,
) -> None:
    session_with_board.add(
        PortalUserProfile(
            sub="chat-user-sub",
            email="chat@example.com",
            full_name="Chat User",
            username="chat_user",
            portal_chat_allowed=True,
        )
    )
    await session_with_board.commit()

    res = await client_admin_board.delete("/api/v1/portal/specialists/chat-user-sub")
    assert_api_error(res, 403, "forbidden")


@pytest.mark.asyncio
async def test_purge_portal_admin_target_forbidden(client_admin_board: AsyncClient) -> None:
    admin = user_portal_admin()
    res = await client_admin_board.delete(f"/api/v1/portal/specialists/{admin.sub}")
    assert_api_error(res, 403, "forbidden")


@pytest.mark.asyncio
async def test_purge_unknown_sub_404(client_admin_board: AsyncClient) -> None:
    res = await client_admin_board.delete("/api/v1/portal/specialists/no-such-sub-xyz")
    assert_api_error(res, 404, "not_found")
