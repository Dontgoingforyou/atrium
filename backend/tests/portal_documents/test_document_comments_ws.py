"""WebSocket тредов комментариев документа: HTTP-тикет и TestClient."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.main import app
from app.portal_chat.comment_thread_events import COMMENT_THREAD_UPDATED_EVENT
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.helpers.portal_test_users import user_portal_admin
from tests.helpers.ws_client import websocket_connect_with_ticket
from tests.portal_documents.conftest import override_dependency


def test_document_comments_ws_rejects_bad_ticket(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with override_dependency(get_db_session, _db):
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                "/api/v1/portal/documents/00000000-0000-0000-0000-00000000aaaa/comments/ws"
                "?ticket=00000000-0000-0000-0000-00000000dead"
            ):
                pass
        assert exc_info.value.code == 4001


def test_document_comments_ws_ticket_and_publish(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_admin),
    ):
        client = TestClient(app, raise_server_exceptions=True)
        doc = client.post(
            "/api/v1/admin/portal-documents",
            json={"title": "WS doc", "body": None, "tag_ids": []},
        )
        assert doc.status_code == 201, doc.text
        doc_id = doc.json()["id"]
        ticket_res = client.post(f"/api/v1/portal/documents/{doc_id}/comments/ws-ticket")
        assert ticket_res.status_code == 201, ticket_res.text
        ticket = ticket_res.json()["ticket"]
        assert len(ticket) >= 8
        with client.websocket_connect(f"/api/v1/portal/documents/{doc_id}/comments/ws?ticket={ticket}") as ws:
            created = client.post(
                f"/api/v1/portal/documents/{doc_id}/comments",
                json={"body": "e2e"},
            )
            assert created.status_code == 201, created.text
            raw = ws.receive_text()
            assert json.loads(raw)["event"] == COMMENT_THREAD_UPDATED_EVENT


def test_document_comments_ws_reconsume_and_mismatch(
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
        a = client.post("/api/v1/admin/portal-documents", json={"title": "WS A", "body": None, "tag_ids": []})
        b = client.post("/api/v1/admin/portal-documents", json={"title": "WS B", "body": None, "tag_ids": []})
        assert a.status_code == 201 and b.status_code == 201
        id_a, id_b = a.json()["id"], b.json()["id"]
        ticket = client.post(f"/api/v1/portal/documents/{id_a}/comments/ws-ticket").json()["ticket"]
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, f"/api/v1/portal/documents/{id_b}/comments/ws", ticket):
                pass
        assert exc_info.value.code == 4001

        ticket2 = client.post(f"/api/v1/portal/documents/{id_a}/comments/ws-ticket").json()["ticket"]
        with websocket_connect_with_ticket(client, f"/api/v1/portal/documents/{id_a}/comments/ws", ticket2):
            pass
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, f"/api/v1/portal/documents/{id_a}/comments/ws", ticket2):
                pass
        assert exc_info.value.code == 4001
