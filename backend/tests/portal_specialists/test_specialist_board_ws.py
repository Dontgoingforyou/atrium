"""WebSocket доски специалистов: тикет и RBAC."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.helpers.portal_test_users import user_portal_admin, user_portal_manager
from tests.helpers.ws_client import websocket_connect_with_ticket
from tests.portal_specialists.conftest import assert_api_error, override_dependency, user_specialist


@pytest.mark.asyncio
async def test_specialist_board_ws_ticket_manager(
    session_with_board: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield session_with_board

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_manager),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post("/api/v1/portal/specialists/board/ws-ticket")
    assert r.status_code == 201
    assert r.json()["ticket"]


@pytest.mark.asyncio
async def test_specialist_board_ws_ticket_forbidden_specialist(
    session_with_board: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield session_with_board

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_specialist),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.post("/api/v1/portal/specialists/board/ws-ticket")
    assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_specialist_board_ws_ticket_requires_auth(
    client_sqlite_only_board: AsyncClient,
) -> None:
    r = await client_sqlite_only_board.post("/api/v1/portal/specialists/board/ws-ticket")
    assert_api_error(r, 401, "unauthorized")


def test_specialist_board_ws_rejects_invalid_ticket(
    session_with_board: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield session_with_board

    with override_dependency(get_db_session, _db):
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                "/api/v1/portal/specialists/board/ws?ticket=00000000-0000-0000-0000-00000000dead"
            ):
                pass
        assert exc_info.value.code == 4001


def test_specialist_board_ws_connect_reconsume_and_wrong_prefix(
    session_with_board: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield session_with_board

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_admin),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post("/api/v1/portal/specialists/board/ws-ticket")
        assert r.status_code == 201
        ticket = r.json()["ticket"]

        path = "/api/v1/portal/specialists/board/ws"
        with websocket_connect_with_ticket(client, path, ticket):
            pass
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, path, ticket):
                pass
        assert exc_info.value.code == 4001

        task_ticket = client.post("/api/v1/portal/tasks/board/ws-ticket").json()["ticket"]
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, path, task_ticket):
                pass
        assert exc_info.value.code == 4001
