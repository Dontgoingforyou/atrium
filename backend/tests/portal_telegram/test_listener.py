"""Redis listener → Telegram send_message."""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMember, PortalChatMessage
from app.infrastructure.db.models.portal_telegram_binding import PortalTelegramBinding
from app.portal_chat.services.inbox_publish import (
    EVENT_DM_INBOX_UPDATE,
    EVENT_DM_INBOX_WITHDRAWN,
    EVENT_PORTAL_NOTIFICATION_UPDATE,
    EVENT_PORTAL_NOTIFICATION_WITHDRAWN,
)
from app.portal_telegram.services import listener as listener_mod
from app.portal_telegram.services.listener import (
    _handle_inbox_payload,
    _send_telegram_message,
    deliver_telegram_inbox_payload,
    telegram_inbox_listener_loop,
)
from sqlalchemy import select
from tests.portal_telegram.conftest import FakeRedisPubSubClient


@pytest.fixture
def patch_listener_session(monkeypatch: pytest.MonkeyPatch, sqlite_session):
    @asynccontextmanager
    async def _sf():
        yield sqlite_session

    monkeypatch.setattr(listener_mod, "async_session_factory", lambda: _sf())


@pytest.mark.asyncio
async def test_send_telegram_message_success(mock_aiogram_bot: MagicMock, tg_settings, monkeypatch) -> None:
    mock_aiogram_bot.send_message = AsyncMock()
    monkeypatch.setattr(listener_mod, "get_bot", lambda: mock_aiogram_bot)
    await _send_telegram_message(1, "hi", tg_settings())
    mock_aiogram_bot.send_message.assert_awaited_once()
    assert mock_aiogram_bot.send_message.await_args.kwargs["disable_web_page_preview"] is True


@pytest.mark.asyncio
async def test_send_telegram_message_forbidden_unlinks(
    mock_aiogram_bot: MagicMock,
    tg_settings,
    sqlite_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="u", telegram_chat_id=42))
    await sqlite_session.commit()

    mock_aiogram_bot.send_message = AsyncMock(
        side_effect=TelegramForbiddenError(MagicMock(), "blocked"),
    )

    @asynccontextmanager
    async def _sess():
        yield sqlite_session

    monkeypatch.setattr(listener_mod, "get_bot", lambda: mock_aiogram_bot)
    monkeypatch.setattr(listener_mod, "async_session_factory", lambda: _sess())

    await _send_telegram_message(42, "x", tg_settings())

    row = await sqlite_session.scalar(select(PortalTelegramBinding).where(PortalTelegramBinding.telegram_chat_id == 42))
    assert row is None


@pytest.mark.asyncio
async def test_send_telegram_message_retries_then_stops(mock_aiogram_bot: MagicMock, tg_settings, monkeypatch) -> None:
    mock_aiogram_bot.send_message = AsyncMock(side_effect=RuntimeError("network"))
    monkeypatch.setattr(listener_mod, "get_bot", lambda: mock_aiogram_bot)
    sleep_mock = AsyncMock()
    monkeypatch.setattr(listener_mod.asyncio, "sleep", sleep_mock)

    await _send_telegram_message(9, "z", tg_settings())

    assert mock_aiogram_bot.send_message.await_count == 4
    assert sleep_mock.await_count == 3


@pytest.mark.asyncio
async def test_send_telegram_message_retry_after_uses_retry_after(
    mock_aiogram_bot: MagicMock,
    tg_settings,
    monkeypatch,
) -> None:
    mock_aiogram_bot.send_message = AsyncMock(
        side_effect=[
            TelegramRetryAfter(MagicMock(), "flood", 2),
            None,
        ]
    )
    monkeypatch.setattr(listener_mod, "get_bot", lambda: mock_aiogram_bot)
    sleep_mock = AsyncMock()
    monkeypatch.setattr(listener_mod.asyncio, "sleep", sleep_mock)

    await _send_telegram_message(9, "z", tg_settings())

    assert mock_aiogram_bot.send_message.await_count == 2
    sleep_mock.assert_awaited_once_with(2.0)


@pytest.mark.asyncio
async def test_send_telegram_message_bad_request_no_retry(
    mock_aiogram_bot: MagicMock,
    tg_settings,
    monkeypatch,
) -> None:
    mock_aiogram_bot.send_message = AsyncMock(side_effect=TelegramBadRequest(MagicMock(), "message is too long"))
    monkeypatch.setattr(listener_mod, "get_bot", lambda: mock_aiogram_bot)
    sleep_mock = AsyncMock()
    monkeypatch.setattr(listener_mod.asyncio, "sleep", sleep_mock)

    await _send_telegram_message(9, "z", tg_settings())

    mock_aiogram_bot.send_message.assert_awaited_once()
    sleep_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbox_payload_no_binding(
    tg_settings,
    patch_listener_session,
    monkeypatch,
) -> None:
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)
    await _handle_inbox_payload(
        "unknown-sub",
        {"event": EVENT_PORTAL_NOTIFICATION_UPDATE, "notification_id": str(uuid.uuid4())},
        tg_settings(),
    )
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbox_notification_missing_skips_send(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=100))
    await sqlite_session.commit()

    monkeypatch.setattr(listener_mod, "fetch_notification_for_recipient", AsyncMock(return_value=None))
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_PORTAL_NOTIFICATION_UPDATE, "notification_id": str(uuid.uuid4())},
        tg_settings(),
    )
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbox_notification_sends(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=200))
    await sqlite_session.commit()

    notif = MagicMock()
    monkeypatch.setattr(listener_mod, "fetch_notification_for_recipient", AsyncMock(return_value=notif))
    monkeypatch.setattr(listener_mod, "mention_subs_from_notification", lambda _n: [])
    monkeypatch.setattr(listener_mod, "fetch_mention_display_labels_longest_first", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        listener_mod,
        "format_portal_notification_telegram",
        lambda *_a, **_kw: ("body text", "https://p.example/t"),
    )
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    nid = uuid.uuid4()
    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_PORTAL_NOTIFICATION_UPDATE, "notification_id": str(nid)},
        tg_settings(),
    )
    send_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_deliver_returns_failed_when_send_fails(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=200))
    await sqlite_session.commit()

    notif = MagicMock()
    monkeypatch.setattr(listener_mod, "fetch_notification_for_recipient", AsyncMock(return_value=notif))
    monkeypatch.setattr(listener_mod, "mention_subs_from_notification", lambda _n: [])
    monkeypatch.setattr(listener_mod, "fetch_mention_display_labels_longest_first", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        listener_mod,
        "format_portal_notification_telegram",
        lambda *_a, **_kw: ("body text", "https://p.example/t"),
    )
    monkeypatch.setattr(listener_mod, "_send_telegram_message", AsyncMock(return_value=False))

    nid = uuid.uuid4()
    outcome = await deliver_telegram_inbox_payload(
        "user-sub",
        {"event": EVENT_PORTAL_NOTIFICATION_UPDATE, "notification_id": str(nid)},
        tg_settings(),
    )
    assert outcome == "failed"


@pytest.mark.asyncio
async def test_handle_inbox_notification_without_id_skips_send(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=201))
    await sqlite_session.commit()
    fetch_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "fetch_notification_for_recipient", fetch_mock)
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_PORTAL_NOTIFICATION_UPDATE},
        tg_settings(),
    )
    fetch_mock.assert_not_awaited()
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbox_notification_invalid_id_skips_send(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=202))
    await sqlite_session.commit()
    fetch_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "fetch_notification_for_recipient", fetch_mock)
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_PORTAL_NOTIFICATION_UPDATE, "notification_id": "not-a-uuid"},
        tg_settings(),
    )
    fetch_mock.assert_not_awaited()
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbox_notification_by_id_calendar_updated(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    """Payload с notification_id грузит конкретное calendar_event_updated, не latest."""
    from app.portal_collab.services._notification_access import NOTIFICATION_TYPE_CALENDAR_EVENT_UPDATED

    sqlite_session.add(PortalTelegramBinding(user_sub="user-b", telegram_chat_id=777))
    await sqlite_session.commit()

    target_id = uuid.uuid4()
    notif = MagicMock()
    notif.type = NOTIFICATION_TYPE_CALENDAR_EVENT_UPDATED
    notif.id = target_id
    fetch_mock = AsyncMock(return_value=notif)
    monkeypatch.setattr(listener_mod, "fetch_notification_for_recipient", fetch_mock)
    monkeypatch.setattr(listener_mod, "mention_subs_from_notification", lambda _n: [])
    monkeypatch.setattr(listener_mod, "fetch_mention_display_labels_longest_first", AsyncMock(return_value=[]))
    monkeypatch.setattr(
        listener_mod,
        "format_portal_notification_telegram",
        lambda n, *_a, **_kw: (f"Событие обновлено id={n.id}", "/calendar"),
    )
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-b",
        {"event": EVENT_PORTAL_NOTIFICATION_UPDATE, "notification_id": str(target_id)},
        tg_settings(),
    )
    fetch_mock.assert_awaited_once()
    assert fetch_mock.await_args.kwargs.get("notification_id") == target_id
    send_mock.assert_awaited_once()
    assert "Событие обновлено" in send_mock.await_args.args[1]


@pytest.mark.asyncio
async def test_handle_dm_skips_deleted_message_without_fallback(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    """Удалённое сообщение не уходит в Telegram, даже если в чате есть более раннее."""
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=310))
    now = datetime.now(UTC)
    cid = uuid.uuid4()
    deleted_id = uuid.uuid4()
    sqlite_session.add(PortalChat(id=cid, title="Чат", created_by_sub="admin-sub", canonical_dm_key=None))
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="user-sub"))
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="admin-sub"))
    sqlite_session.add(
        PortalChatMessage(
            chat_id=cid,
            author_sub="admin-sub",
            body="старое",
            created_at=now - timedelta(minutes=5),
        )
    )
    sqlite_session.add(
        PortalChatMessage(
            id=deleted_id,
            chat_id=cid,
            author_sub="admin-sub",
            body="секрет",
            created_at=now,
            deleted_for_all_at=now,
        )
    )
    await sqlite_session.commit()

    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)
    await _handle_inbox_payload(
        "user-sub",
        {
            "event": EVENT_DM_INBOX_UPDATE,
            "chat_id": str(cid),
            "kind": "dm",
            "message_id": str(deleted_id),
        },
        tg_settings(),
    )
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event",
    [EVENT_PORTAL_NOTIFICATION_WITHDRAWN, EVENT_DM_INBOX_WITHDRAWN],
)
async def test_withdraw_events_are_not_sent_to_telegram(
    event: str,
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=311))
    await sqlite_session.commit()
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)
    await _handle_inbox_payload(
        "user-sub",
        {"event": event, "chat_id": str(uuid.uuid4()), "message_id": str(uuid.uuid4())},
        tg_settings(),
    )
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_dm_missing_chat_id(tg_settings, sqlite_session, patch_listener_session, monkeypatch) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=300))
    await sqlite_session.commit()

    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_DM_INBOX_UPDATE, "kind": "dm"},
        tg_settings(),
    )
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_dm_bad_chat_id(tg_settings, sqlite_session, patch_listener_session, monkeypatch) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=400))
    await sqlite_session.commit()

    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_DM_INBOX_UPDATE, "chat_id": "not-a-uuid"},
        tg_settings(),
    )
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_dm_format_returns_none(tg_settings, sqlite_session, patch_listener_session, monkeypatch) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=500))
    await sqlite_session.commit()
    cid = uuid.uuid4()

    monkeypatch.setattr(listener_mod, "format_chat_inbox_telegram", AsyncMock(return_value=None))
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_DM_INBOX_UPDATE, "chat_id": str(cid)},
        tg_settings(),
    )
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_dm_group_sends(tg_settings, sqlite_session, patch_listener_session, monkeypatch) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=600))
    await sqlite_session.commit()
    cid = uuid.uuid4()

    monkeypatch.setattr(
        listener_mod,
        "format_chat_inbox_telegram",
        AsyncMock(return_value=("dm body", "https://p.example/chats")),
    )
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_DM_INBOX_UPDATE, "chat_id": str(cid), "kind": "group"},
        tg_settings(),
    )
    send_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_dm_skips_telegram_when_unread_at_suppress_threshold(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=610))
    await sqlite_session.commit()
    cid = uuid.uuid4()

    monkeypatch.setattr(listener_mod, "get_batch_unread_counts", AsyncMock(return_value={cid: 3}))
    fmt = AsyncMock()
    monkeypatch.setattr(listener_mod, "format_chat_inbox_telegram", fmt)
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_DM_INBOX_UPDATE, "chat_id": str(cid), "kind": "dm"},
        tg_settings(),
    )
    fmt.assert_not_awaited()
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_dm_sends_when_unread_below_suppress_threshold(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=611))
    await sqlite_session.commit()
    cid = uuid.uuid4()

    monkeypatch.setattr(listener_mod, "get_batch_unread_counts", AsyncMock(return_value={cid: 2}))
    monkeypatch.setattr(
        listener_mod,
        "format_chat_inbox_telegram",
        AsyncMock(return_value=("body", "https://p.example/c")),
    )
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_DM_INBOX_UPDATE, "chat_id": str(cid), "kind": "dm"},
        tg_settings(),
    )
    send_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_group_skips_telegram_when_unread_at_suppress_threshold(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=612))
    await sqlite_session.commit()
    cid = uuid.uuid4()

    monkeypatch.setattr(listener_mod, "get_batch_unread_counts", AsyncMock(return_value={cid: 3}))
    fmt = AsyncMock()
    monkeypatch.setattr(listener_mod, "format_chat_inbox_telegram", fmt)
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_DM_INBOX_UPDATE, "chat_id": str(cid), "kind": "group"},
        tg_settings(),
    )
    fmt.assert_not_awaited()
    send_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_inbox_sends_when_recipient_mentioned_despite_high_unread(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=613))
    await sqlite_session.commit()
    cid = uuid.uuid4()

    monkeypatch.setattr(listener_mod, "get_batch_unread_counts", AsyncMock(return_value={cid: 10}))
    monkeypatch.setattr(
        listener_mod,
        "format_chat_inbox_telegram",
        AsyncMock(return_value=("m", "https://p.example/m")),
    )
    send_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_send_telegram_message", send_mock)

    await _handle_inbox_payload(
        "user-sub",
        {
            "event": EVENT_DM_INBOX_UPDATE,
            "chat_id": str(cid),
            "kind": "dm",
            "recipient_mentioned": True,
        },
        tg_settings(),
    )
    send_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_dm_invalid_kind_defaults_to_dm(
    tg_settings,
    sqlite_session,
    patch_listener_session,
    monkeypatch,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=601))
    await sqlite_session.commit()
    cid = uuid.uuid4()

    fmt = AsyncMock(return_value=("t", "https://x"))
    monkeypatch.setattr(listener_mod, "format_chat_inbox_telegram", fmt)
    monkeypatch.setattr(listener_mod, "_send_telegram_message", AsyncMock())

    await _handle_inbox_payload(
        "user-sub",
        {"event": EVENT_DM_INBOX_UPDATE, "chat_id": str(cid), "kind": "weird"},
        tg_settings(),
    )
    assert fmt.await_args.kwargs["kind"] == "dm"


@pytest.mark.asyncio
async def test_listener_loop_processes_pmessage_and_cancellable(
    tg_settings,
    monkeypatch,
) -> None:
    payload = {"event": EVENT_DM_INBOX_UPDATE, "chat_id": str(uuid.uuid4())}
    redis_client = FakeRedisPubSubClient(
        [
            {"type": "subscribe"},
            {
                "type": "pmessage",
                "channel": "inbox:user-sub",
                "data": json.dumps(payload),
            },
        ]
    )
    handle_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_handle_inbox_payload", handle_mock)
    monkeypatch.setattr(listener_mod, "get_settings", tg_settings)

    task = asyncio.create_task(telegram_inbox_listener_loop(redis_client))  # type: ignore[arg-type]
    await asyncio.sleep(0.15)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    handle_mock.assert_awaited()


@pytest.mark.asyncio
async def test_listener_loop_channel_bytes_user_sub(
    tg_settings,
    monkeypatch,
) -> None:
    payload = {"event": EVENT_DM_INBOX_UPDATE, "chat_id": str(uuid.uuid4())}
    redis_client = FakeRedisPubSubClient(
        [{"type": "pmessage", "channel": b"inbox:abc", "data": json.dumps(payload)}],
    )
    handle_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_handle_inbox_payload", handle_mock)
    monkeypatch.setattr(listener_mod, "get_settings", tg_settings)

    task = asyncio.create_task(telegram_inbox_listener_loop(redis_client))  # type: ignore[arg-type]
    await asyncio.sleep(0.15)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    handle_mock.assert_awaited_once()
    assert handle_mock.await_args.args[0] == "abc"


@pytest.mark.asyncio
async def test_listener_loop_skips_non_json(tg_settings, monkeypatch) -> None:
    redis_client = FakeRedisPubSubClient(
        [{"type": "pmessage", "channel": "inbox:user-sub", "data": b"{{"}],
    )
    handle_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_handle_inbox_payload", handle_mock)
    monkeypatch.setattr(listener_mod, "get_settings", tg_settings)

    task = asyncio.create_task(telegram_inbox_listener_loop(redis_client))  # type: ignore[arg-type]
    await asyncio.sleep(0.12)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    handle_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_listener_loop_skips_non_pmessage(tg_settings, monkeypatch) -> None:
    redis_client = FakeRedisPubSubClient(
        [{"type": "message", "channel": "inbox:user-sub", "data": "{}"}],
    )
    handle_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_handle_inbox_payload", handle_mock)
    monkeypatch.setattr(listener_mod, "get_settings", tg_settings)

    task = asyncio.create_task(telegram_inbox_listener_loop(redis_client))  # type: ignore[arg-type]
    await asyncio.sleep(0.12)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    handle_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_listener_loop_skips_bad_channel(tg_settings, monkeypatch) -> None:
    redis_client = FakeRedisPubSubClient(
        [{"type": "pmessage", "channel": "other:chan", "data": "{}"}],
    )
    handle_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_handle_inbox_payload", handle_mock)
    monkeypatch.setattr(listener_mod, "get_settings", tg_settings)

    task = asyncio.create_task(telegram_inbox_listener_loop(redis_client))  # type: ignore[arg-type]
    await asyncio.sleep(0.12)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    handle_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_listener_loop_skips_missing_channel_or_data(tg_settings, monkeypatch) -> None:
    redis_client = FakeRedisPubSubClient(
        [{"type": "pmessage", "channel": None, "data": "{}"}],
    )
    handle_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_handle_inbox_payload", handle_mock)
    monkeypatch.setattr(listener_mod, "get_settings", tg_settings)

    task = asyncio.create_task(telegram_inbox_listener_loop(redis_client))  # type: ignore[arg-type]
    await asyncio.sleep(0.12)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    handle_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_listener_loop_skips_non_dict_payload(tg_settings, monkeypatch) -> None:
    redis_client = FakeRedisPubSubClient(
        [{"type": "pmessage", "channel": "inbox:user-sub", "data": json.dumps([1, 2])}],
    )
    handle_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_handle_inbox_payload", handle_mock)
    monkeypatch.setattr(listener_mod, "get_settings", tg_settings)

    task = asyncio.create_task(telegram_inbox_listener_loop(redis_client))  # type: ignore[arg-type]
    await asyncio.sleep(0.12)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    handle_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_listener_loop_handler_exception_survives(
    tg_settings,
    monkeypatch,
) -> None:
    payload = {"event": EVENT_DM_INBOX_UPDATE, "chat_id": str(uuid.uuid4())}
    redis_client = FakeRedisPubSubClient(
        [
            {"type": "pmessage", "channel": "inbox:user-sub", "data": json.dumps(payload)},
            {"type": "pmessage", "channel": "inbox:user-sub", "data": json.dumps(payload)},
        ],
    )
    calls = 0

    async def boom(*_a: object, **_kw: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("handler boom")

    monkeypatch.setattr(listener_mod, "_handle_inbox_payload", boom)
    monkeypatch.setattr(listener_mod, "get_settings", tg_settings)

    task = asyncio.create_task(telegram_inbox_listener_loop(redis_client))  # type: ignore[arg-type]
    await asyncio.sleep(0.2)
    assert not task.done()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert calls == 2


@pytest.mark.asyncio
async def test_listener_loop_pubsub_crash_then_reconnect(tg_settings, monkeypatch) -> None:
    """Внутренний try ловит сбой pubsub, sleep(3), второй заход в цикл."""

    class BoomCm:
        async def __aenter__(self) -> None:
            raise RuntimeError("pubsub broken")

        async def __aexit__(self, *_x: object) -> None:
            return None

    nice = FakeRedisPubSubClient(
        [{"type": "pmessage", "channel": "inbox:z", "data": "{}"}],
    )

    redis_mock = MagicMock()
    redis_mock.pubsub = MagicMock(side_effect=[BoomCm(), nice.pubsub()])

    sleeps: list[float] = []

    orig_sleep = asyncio.sleep

    async def sleep_wrap(delay: float) -> None:
        sleeps.append(delay)
        # обходим только паузу переподключения listener (ровно 3 с), не sleep внутри fake listen()
        if abs(delay - 3.0) < 0.01:
            return
        await orig_sleep(delay)

    monkeypatch.setattr(listener_mod, "get_settings", tg_settings)
    monkeypatch.setattr(listener_mod.asyncio, "sleep", sleep_wrap)

    handle_mock = AsyncMock()
    monkeypatch.setattr(listener_mod, "_handle_inbox_payload", handle_mock)

    task = asyncio.create_task(telegram_inbox_listener_loop(redis_mock))  # type: ignore[arg-type]
    await asyncio.sleep(0.25)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert any(s >= 3.0 for s in sleeps)
