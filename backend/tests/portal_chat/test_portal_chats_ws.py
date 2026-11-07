"""WebSocket чатов: тикет, connect, доставка, ephemeral. Не звать хэндлер напрямую."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.infrastructure.ws.inbox_manager import InboxManager
from app.main import app
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b
from tests.helpers.ws_client import websocket_connect_with_ticket
from tests.portal_chat.conftest import CHAT_API, as_user_b, assert_api_error, override_dependency


def test_ws_chat_rejects_invalid_ticket(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with override_dependency(get_db_session, _db):
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(
                f"{CHAT_API}/chats/{uuid.uuid4()}/ws?ticket=00000000-0000-0000-0000-00000000dead"
            ):
                pass
        assert exc_info.value.code == 4001


async def test_ws_ticket_forbidden_for_non_member(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    r = await client_admin.post(
        f"{CHAT_API}/chats",
        json={"title": "WS-тест", "member_subs": [user_portal_regular().sub]},
    )
    chat_id = r.json()["id"]
    with as_user_b():
        r2 = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/ws-ticket")
    assert_api_error(r2, 403, "forbidden")


async def test_inbox_ws_ticket_201(client_admin: AsyncClient) -> None:
    r = await client_admin.post(f"{CHAT_API}/inbox/ws-ticket")
    assert r.status_code == 201, r.text
    assert len(r.json()["ticket"]) > 8


async def test_post_chat_ws_ticket_201(client_admin: AsyncClient) -> None:
    r_chat = await client_admin.post(
        f"{CHAT_API}/chats",
        json={"title": "WS tk", "member_subs": [user_portal_regular().sub]},
    )
    chat_id = r_chat.json()["id"]
    r = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/ws-ticket")
    assert r.status_code == 201
    assert "ticket" in r.json()


def test_ws_inbox_rejects_invalid_ticket(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with override_dependency(get_db_session, _db):
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, f"{CHAT_API}/inbox/ws", "00000000-0000-0000-0000-00000000dead"):
                pass
        assert exc_info.value.code == 4001


def test_ws_chat_ticket_chat_id_mismatch_closes_4001(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    path_id = uuid.uuid4()
    ticket_id = uuid.uuid4()
    with (
        override_dependency(get_db_session, _db),
        patch(
            "app.infrastructure.ws.tickets.consume_chat_ws_ticket",
            new=AsyncMock(return_value=(ticket_id, user_portal_admin())),
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"{CHAT_API}/chats/{path_id}/ws?ticket=any-valid-looking"):
                pass
        assert exc_info.value.code == 4001


async def test_ws_chat_orphan_member_not_accessible_4001(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    from datetime import UTC, datetime

    from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMember

    now = datetime.now(UTC)
    orphan_id = uuid.uuid4()
    sqlite_session.add(
        PortalChat(
            id=orphan_id,
            title=None,
            created_by_sub=user_portal_admin().sub,
            created_at=now,
            updated_at=now,
            canonical_dm_key=None,
        )
    )
    sqlite_session.add(PortalChatMember(chat_id=orphan_id, user_sub=user_portal_admin().sub, joined_at=now))
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        patch(
            "app.infrastructure.ws.tickets.consume_chat_ws_ticket",
            new=AsyncMock(return_value=(orphan_id, user_portal_admin())),
        ),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"{CHAT_API}/chats/{orphan_id}/ws?ticket=orphan-ticket"):
                pass
        assert exc_info.value.code == 4001


def test_ws_chat_second_ticket_consume_closes_4001(
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
        r_chat = client.post(
            f"{CHAT_API}/chats",
            json={"title": "Reuse", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r_chat.json()["id"]
        r_t = client.post(f"{CHAT_API}/chats/{chat_id}/ws-ticket")
        ticket = r_t.json()["ticket"]
        with websocket_connect_with_ticket(client, f"{CHAT_API}/chats/{chat_id}/ws", ticket):
            pass
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, f"{CHAT_API}/chats/{chat_id}/ws", ticket):
                pass
        assert exc_info.value.code == 4001


def test_ws_chat_delivers_message_created(
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
        r_chat = client.post(
            f"{CHAT_API}/chats",
            json={"title": "Live", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r_chat.json()["id"]
        r_t = client.post(f"{CHAT_API}/chats/{chat_id}/ws-ticket")
        ticket = r_t.json()["ticket"]
        with websocket_connect_with_ticket(client, f"{CHAT_API}/chats/{chat_id}/ws", ticket) as ws:
            r_msg = client.post(f"{CHAT_API}/chats/{chat_id}/messages", json={"body": "по WS"})
            assert r_msg.status_code == 201, r_msg.text
            raw = ws.receive_text()
            data = json.loads(raw)
            assert data["event"] == "message_created"
            assert data["message"]["body"] == "по WS"
            assert data["message"]["id"] == r_msg.json()["id"]


def test_ws_admin_listener_cannot_send_typing(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """Admin без членства читает WS, но ephemeral write закрывает 4001."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_regular),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        r_chat = client.post(
            f"{CHAT_API}/chats",
            json={"title": "Чужой", "member_subs": [user_portal_user_b().sub]},
        )
        chat_id = r_chat.json()["id"]

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_admin),
    ):
        client = TestClient(app, raise_server_exceptions=False)
        r_t = client.post(f"{CHAT_API}/chats/{chat_id}/ws-ticket")
        assert r_t.status_code == 201, r_t.text
        ticket = r_t.json()["ticket"]
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with websocket_connect_with_ticket(client, f"{CHAT_API}/chats/{chat_id}/ws", ticket) as ws:
                ws.send_text(json.dumps({"event": "typing", "active": True}))
                ws.receive_text()
        assert exc_info.value.code == 4001


def test_ws_chat_pong_keeps_connection(
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
        r_chat = client.post(
            f"{CHAT_API}/chats",
            json={"title": "Pong", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r_chat.json()["id"]
        r_t = client.post(f"{CHAT_API}/chats/{chat_id}/ws-ticket")
        ticket = r_t.json()["ticket"]
        with websocket_connect_with_ticket(client, f"{CHAT_API}/chats/{chat_id}/ws", ticket) as ws:
            ws.send_text('{"type":"pong"}')
            r_msg = client.post(f"{CHAT_API}/chats/{chat_id}/messages", json={"body": "после pong"})
            assert r_msg.status_code == 201, r_msg.text
            raw = ws.receive_text()
            assert json.loads(raw)["event"] == "message_created"


def test_inbox_ws_presence_update_includes_last_seen_at(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    published: list[dict] = []

    async def _capture(_self: InboxManager, payload: dict) -> None:
        published.append(payload)

    with (
        override_dependency(get_db_session, _db),
        override_dependency(get_current_user, user_portal_admin),
        patch.object(InboxManager, "publish_presence", new=_capture),
        patch("app.portal_chat.routes.inbox.set_last_seen_iso_now", new_callable=AsyncMock) as mock_iso,
    ):
        client = TestClient(app, raise_server_exceptions=False)
        r = client.post(f"{CHAT_API}/inbox/ws-ticket")
        ticket = r.json()["ticket"]
        with websocket_connect_with_ticket(client, f"{CHAT_API}/inbox/ws", ticket):
            pass

    assert len(published) == 2
    admin_sub = user_portal_admin().sub
    assert published[0]["status"] == "online"
    assert published[0]["sub"] == admin_sub
    assert published[0].get("last_seen_at")
    assert published[1]["status"] == "offline"
    assert published[1]["sub"] == admin_sub
    assert published[1].get("last_seen_at")
    mock_iso.assert_awaited_once_with(user_sub=admin_sub)
