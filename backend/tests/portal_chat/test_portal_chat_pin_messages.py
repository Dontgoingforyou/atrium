"""Тесты закрепления сообщений чата.

Покрытие:
- успешный сценарий pin/unpin/list на сервисном уровне
- 403 для не-участника чата на уровне HTTP
- валидация: удалённое сообщение, лимит закреплённых сообщений на чат
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.main import app
from app.portal_chat.schemas.chat import PortalChatMessageCreate
from app.portal_chat.services import _mutations_pin as pin_svc
from app.portal_chat.services import chat as chat_svc
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b

async def _fresh(session: AsyncSession, msg: object) -> None:
    """post_message кладёт в ``attachments`` обычный список — без этого flush после падает."""
    msg.__dict__.pop("attachments", None)  # type: ignore[union-attr]
    await session.refresh(msg)  # type: ignore[arg-type]

@pytest.fixture(autouse=True)
def _mock_chat_and_inbox_publish() -> object:
    """pin/unpin и post_message публикуют события в WS — без реального Redis."""
    mgr = MagicMock(publish=AsyncMock())
    with (
        patch("app.infrastructure.ws.managers.get_chat_manager", return_value=mgr),
        patch("app.infrastructure.ws.inbox_manager.get_inbox_manager", return_value=mgr),
    ):
        yield

async def test_pin_message_success(sqlite_session: AsyncSession) -> None:
    """Закрепление сообщения устанавливает pinned_at и pinned_by_sub."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="закрепи меня"))
    await _fresh(sqlite_session, msg)

    pinned = await pin_svc.pin_message(sqlite_session, other, chat.id, msg.id)

    assert pinned.pinned_at is not None
    assert pinned.pinned_by_sub == other.sub

async def test_pin_message_idempotent(sqlite_session: AsyncSession) -> None:
    """Повторное закрепление уже закреплённого сообщения не меняет pinned_by_sub."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="x"))
    await _fresh(sqlite_session, msg)

    first = await pin_svc.pin_message(sqlite_session, admin, chat.id, msg.id)
    second = await pin_svc.pin_message(sqlite_session, other, chat.id, msg.id)

    assert second.pinned_by_sub == first.pinned_by_sub == admin.sub
    assert second.pinned_at == first.pinned_at

async def test_unpin_message_success(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="x"))
    await _fresh(sqlite_session, msg)
    await pin_svc.pin_message(sqlite_session, admin, chat.id, msg.id)
    await _fresh(sqlite_session, msg)

    unpinned = await pin_svc.unpin_message(sqlite_session, other, chat.id, msg.id)

    assert unpinned.pinned_at is None
    assert unpinned.pinned_by_sub is None

async def test_unpin_message_not_pinned_is_noop(sqlite_session: AsyncSession) -> None:
    """Открепление уже незакреплённого сообщения не падает."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="x"))

    unpinned = await pin_svc.unpin_message(sqlite_session, admin, chat.id, msg.id)

    assert unpinned.pinned_at is None

async def test_pin_message_not_found(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)

    with pytest.raises(NotFoundError, match="не найдено"):
        await pin_svc.pin_message(sqlite_session, admin, chat.id, uuid.uuid4())

async def test_pin_deleted_message_validation(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="удалю"))
    msg.__dict__.pop("attachments", None)
    await sqlite_session.refresh(msg)
    mid = msg.id

    with patch("app.portal_chat.services._mutations.async_delete_object", new_callable=AsyncMock):
        await chat_svc.delete_message_for_all(sqlite_session, admin, chat.id, mid)

    with pytest.raises(ValidationError, match="удалённое"):
        await pin_svc.pin_message(sqlite_session, admin, chat.id, mid)

async def test_pin_message_over_limit_raises_validation(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Превышение CHAT_PINNED_MESSAGES_MAX_PER_CHAT — ValidationError."""
    monkeypatch.setattr(pin_svc, "CHAT_PINNED_MESSAGES_MAX_PER_CHAT", 2)
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    m1 = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="1"))
    await _fresh(sqlite_session, m1)
    m2 = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="2"))
    await _fresh(sqlite_session, m2)
    m3 = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="3"))
    await _fresh(sqlite_session, m3)

    await pin_svc.pin_message(sqlite_session, admin, chat.id, m1.id)
    await pin_svc.pin_message(sqlite_session, admin, chat.id, m2.id)

    with pytest.raises(ValidationError, match="максимум"):
        await pin_svc.pin_message(sqlite_session, admin, chat.id, m3.id)

async def test_pin_message_non_member_forbidden(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    user_b = user_portal_user_b()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="x"))

    with pytest.raises(ForbiddenError):
        await pin_svc.pin_message(sqlite_session, user_b, chat.id, msg.id)

async def test_list_pinned_messages_recent_first(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    m1 = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="1"))
    await _fresh(sqlite_session, m1)
    m2 = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="2"))
    await _fresh(sqlite_session, m2)

    await pin_svc.pin_message(sqlite_session, admin, chat.id, m1.id)
    await pin_svc.pin_message(sqlite_session, admin, chat.id, m2.id)

    pinned = await pin_svc.list_pinned_messages(sqlite_session, admin, chat.id)

    assert [m.id for m in pinned] == [m2.id, m1.id]

async def test_list_pinned_messages_empty(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)

    pinned = await pin_svc.list_pinned_messages(sqlite_session, admin, chat.id)

    assert pinned == []

# ---------------------------------------------------------------------------
# HTTP-уровень: /portal/chats/{id}/messages/{mid}/pin, .../pin (DELETE), .../pinned
# ---------------------------------------------------------------------------

async def test_pin_unpin_routes_success(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Чат с закреплением", "member_subs": [user_portal_regular().sub]},
    )
    assert r_chat.status_code == 201
    chat_id = r_chat.json()["id"]

    r_msg = await client_admin.post(
        f"/api/v1/portal/chats/{chat_id}/messages",
        json={"body": "важное сообщение"},
    )
    assert r_msg.status_code == 201
    message_id = r_msg.json()["id"]

    r_pin = await client_admin.post(f"/api/v1/portal/chats/{chat_id}/messages/{message_id}/pin")
    assert r_pin.status_code == 200, r_pin.text
    assert r_pin.json()["pinned_at"] is not None
    assert r_pin.json()["pinned_by_sub"] == user_portal_admin().sub

    r_list = await client_admin.get(f"/api/v1/portal/chats/{chat_id}/messages/pinned")
    assert r_list.status_code == 200
    assert [m["id"] for m in r_list.json()] == [message_id]

    r_unpin = await client_admin.delete(f"/api/v1/portal/chats/{chat_id}/messages/{message_id}/pin")
    assert r_unpin.status_code == 200
    assert r_unpin.json()["pinned_at"] is None

    r_list_after = await client_admin.get(f"/api/v1/portal/chats/{chat_id}/messages/pinned")
    assert r_list_after.json() == []

async def test_pin_message_route_403_non_member(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    """403 при попытке закрепить сообщение в чате, где пользователь не участник."""

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_chat = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Закрытый", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r_chat.json()["id"]
        r_msg = await ac.post(f"/api/v1/portal/chats/{chat_id}/messages", json={"body": "x"})
        message_id = r_msg.json()["id"]

    app.dependency_overrides[get_current_user] = user_portal_user_b
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/portal/chats/{chat_id}/messages/{message_id}/pin")
    from tests.portal_chat.conftest import assert_api_error

    assert_api_error(r, 403, "forbidden")

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)

async def test_list_pinned_messages_route_403_non_member(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_chat = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Закрытый", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r_chat.json()["id"]

    app.dependency_overrides[get_current_user] = user_portal_user_b
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(f"/api/v1/portal/chats/{chat_id}/messages/pinned")
    from tests.portal_chat.conftest import assert_api_error

    assert_api_error(r, 403, "forbidden")

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)
