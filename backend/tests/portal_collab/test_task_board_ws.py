"""WebSocket доски задач: HTTP-тикет и TestClient."""

from __future__ import annotations

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.main import app
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.helpers.portal_test_users import user_portal_admin
from tests.helpers.ws_client import websocket_connect_with_ticket
from tests.portal_collab.conftest import override_dependency


@pytest.mark.asyncio
async def test_task_board_ws_ticket_returns_ticket(
    client_admin: AsyncClient,
) -> None:
    r = await client_admin.post("/api/v1/portal/tasks/board/ws-ticket")
    assert r.status_code == 201, r.text
    assert len(r.json().get("ticket", "")) >= 8


def test_task_board_ws_rejects_invalid_ticket(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> object:
        yield sqlite_session

    with override_dependency(get_db_session, _db):
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            dead = "00000000-0000-0000-0000-00000000dead"
            with client.websocket_connect(f"/api/v1/portal/tasks/board/ws?ticket={dead}"):
                pass
        assert exc_info.value.code == 4001


def test_task_board_ws_connect_disconnect(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> object:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_admin),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post("/api/v1/portal/tasks/board/ws-ticket")
        assert r.status_code == 201, r.text
        ticket = r.json()["ticket"]

        path = "/api/v1/portal/tasks/board/ws"
        with websocket_connect_with_ticket(client, path, ticket) as ws:
            ws.send_text('{"ping": true}')
