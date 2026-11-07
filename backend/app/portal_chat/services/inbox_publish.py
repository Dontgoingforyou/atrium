"""Публикация событий в пер-пользовательский inbox (Redis → WebSocket)."""

from __future__ import annotations

import asyncio
import uuid
from typing import Literal

from app.infrastructure.ws.inbox_manager import get_inbox_manager

EVENT_DM_INBOX_UPDATE = "dm_inbox_update"
EVENT_DM_INBOX_WITHDRAWN = "dm_inbox_withdrawn"
EVENT_PORTAL_NOTIFICATION_UPDATE = "portal_notification_update"
EVENT_PORTAL_NOTIFICATION_WITHDRAWN = "portal_notification_withdrawn"

InboxChatKind = Literal["dm", "group"]


async def publish_chat_list_refresh(
    recipient_sub: str,
    chat_id: uuid.UUID,
    *,
    kind: InboxChatKind = "dm",
    author_sub: str | None = None,
    preview_text: str | None = None,
    is_direct: bool | None = None,
    chat_title: str | None = None,
    recipient_mentioned: bool = False,
    message_id: uuid.UUID | None = None,
) -> None:
    """Сигнал клиенту обновить список чатов (и счётчики). ``kind`` — для UI (звук DM только при ``dm``).

    Дополнительные поля опциональны — старые клиенты их игнорируют.
    ``recipient_mentioned`` — получатель указан в ``mentions`` сообщения (принудительный звук в ЛС).
    """
    payload: dict[str, object] = {
        "event": EVENT_DM_INBOX_UPDATE,
        "chat_id": str(chat_id),
        "kind": kind,
    }
    if author_sub is not None:
        payload["author_sub"] = author_sub
    if preview_text is not None:
        payload["preview_text"] = preview_text
    if is_direct is not None:
        payload["is_direct"] = is_direct
    if chat_title is not None:
        payload["chat_title"] = chat_title
    if recipient_mentioned:
        payload["recipient_mentioned"] = True
    if message_id is not None:
        payload["message_id"] = str(message_id)
    await get_inbox_manager().publish(recipient_sub, payload)


async def publish_dm_inbox_update(recipient_sub: str, chat_id: uuid.UUID) -> None:
    """Обратная совместимость: то же, что ``publish_chat_list_refresh(..., kind='dm')``."""
    await publish_chat_list_refresh(recipient_sub, chat_id, kind="dm")


async def publish_portal_notification_update(
    recipient_sub: str,
    *,
    notification_id: uuid.UUID | str | None = None,
) -> None:
    payload: dict[str, object] = {"event": EVENT_PORTAL_NOTIFICATION_UPDATE}
    if notification_id is not None:
        payload["notification_id"] = str(notification_id)
    await get_inbox_manager().publish(recipient_sub, payload)


async def publish_portal_notification_updates(
    recipient_subs: list[str],
    *,
    notification_ids_by_sub: dict[str, uuid.UUID] | None = None,
) -> None:
    """Параллельная публикация inbox-сигнала нескольким получателям.

    ``notification_ids_by_sub`` — опционально id конкретного уведомления.
    """
    if not recipient_subs:
        return
    ids = notification_ids_by_sub or {}
    await asyncio.gather(
        *(publish_portal_notification_update(sub, notification_id=ids.get(sub)) for sub in recipient_subs)
    )


async def publish_portal_notification_withdrawals(recipient_subs: list[str]) -> None:
    """Сигнал перечитать колокольчик: строк уведомления уже нет. Без звука на клиенте."""
    if not recipient_subs:
        return
    payload: dict[str, object] = {"event": EVENT_PORTAL_NOTIFICATION_WITHDRAWN}
    await asyncio.gather(*(get_inbox_manager().publish(sub, payload) for sub in recipient_subs))


async def publish_chat_inbox_withdrawals(
    recipient_subs: list[str],
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
) -> None:
    """Снять тост и системное уведомление о сообщении, которого уже нет."""
    if not recipient_subs:
        return
    payload: dict[str, object] = {
        "event": EVENT_DM_INBOX_WITHDRAWN,
        "chat_id": str(chat_id),
        "message_id": str(message_id),
    }
    await asyncio.gather(*(get_inbox_manager().publish(sub, payload) for sub in recipient_subs))
