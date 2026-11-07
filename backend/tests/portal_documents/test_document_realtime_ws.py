"""WebSocket карточки документа и дерева навигации: HTTP-тикет и TestClient."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.main import app
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.helpers.portal_test_users import user_portal_admin
from tests.helpers.ws_client import websocket_connect_with_ticket
from tests.portal_documents.conftest import override_dependency


def test_document_page_ws_rejects_bad_ticket(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with override_dependency(get_db_session, _db):
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                "/api/v1/portal/documents/00000000-0000-0000-0000-00000000aaaa/content-ws"
                "?ticket=00000000-0000-0000-0000-00000000dead"
            ):
                pass
        assert exc_info.value.code == 4001


def test_document_page_ws_ticket_mismatch_prefix_and_reconsume(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_admin),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        a = client.post("/api/v1/admin/portal-documents", json={"title": "Page A", "body": None, "tag_ids": []})
        b = client.post("/api/v1/admin/portal-documents", json={"title": "Page B", "body": None, "tag_ids": []})
        assert a.status_code == 201 and b.status_code == 201
        id_a, id_b = a.json()["id"], b.json()["id"]

        page_ticket = client.post(f"/api/v1/portal/documents/{id_a}/content-ws-ticket")
        assert page_ticket.status_code == 201, page_ticket.text
        ticket = page_ticket.json()["ticket"]
        assert len(ticket) >= 8

        comments_ticket = client.post(f"/api/v1/portal/documents/{id_a}/comments/ws-ticket").json()["ticket"]
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, f"/api/v1/portal/documents/{id_a}/content-ws", comments_ticket):
                pass
        assert exc_info.value.code == 4001

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, f"/api/v1/portal/documents/{id_b}/content-ws", ticket):
                pass
        assert exc_info.value.code == 4001

        ticket2 = client.post(f"/api/v1/portal/documents/{id_a}/content-ws-ticket").json()["ticket"]
        with websocket_connect_with_ticket(client, f"/api/v1/portal/documents/{id_a}/content-ws", ticket2):
            pass
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, f"/api/v1/portal/documents/{id_a}/content-ws", ticket2):
                pass
        assert exc_info.value.code == 4001


def test_nav_tree_ws_ticket_and_reconsume(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_admin),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post("/api/v1/portal/navigation-tree-ws-ticket")
        assert r.status_code == 201, r.text
        ticket = r.json()["ticket"]
        assert len(ticket) >= 8

        with websocket_connect_with_ticket(client, "/api/v1/portal/navigation-tree-ws", ticket):
            pass
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, "/api/v1/portal/navigation-tree-ws", ticket):
                pass
        assert exc_info.value.code == 4001

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                "/api/v1/portal/navigation-tree-ws?ticket=00000000-0000-0000-0000-00000000dead"
            ):
                pass
        assert exc_info.value.code == 4001
