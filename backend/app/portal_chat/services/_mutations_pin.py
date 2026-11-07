"""Закрепление / открепление сообщений чата."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMessage
from app.infrastructure.ws.managers import get_chat_manager
from app.portal_chat.constants import CHAT_PINNED_MESSAGES_MAX_PER_CHAT
from app.portal_chat.services._queries import (
    _ensure_chat_access,
    ensure_chat_read_access,
    get_visible_message_or_404,
)
from app.portal_chat.services._queries_messages import (
    _load_attachments_and_hydrate_reads,
    _not_hidden_for_user_sub,
    message_to_read,
)
from app.schemas.auth import UserPublic


async def _publish_message_updated(chat_id: uuid.UUID, msg: PortalChatMessage) -> None:
    read = message_to_read(msg)
    await get_chat_manager().publish(
        chat_id,
        {"event": "message_updated", "message": read.model_dump(mode="json")},
    )


async def pin_message(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
) -> PortalChatMessage:
    """Закрепляет сообщение в чате. Доступно любому участнику чата."""
    await _ensure_chat_access(session, user, chat_id)
    msg = await get_visible_message_or_404(session, user, chat_id, message_id)
    if msg.deleted_for_all_at is not None:
        raise ValidationError("Нельзя закрепить удалённое сообщение")

    if msg.pinned_at is None:
        chat_row = (
            await session.execute(select(PortalChat).where(PortalChat.id == chat_id).with_for_update())
        ).scalar_one()
        chat_row.updated_at = _now_utc()
        await session.flush()
        count_stmt = select(func.count(PortalChatMessage.id)).where(
            PortalChatMessage.chat_id == chat_id,
            PortalChatMessage.pinned_at.is_not(None),
        )
        pinned_count = (await session.execute(count_stmt)).scalar_one()
        if pinned_count >= CHAT_PINNED_MESSAGES_MAX_PER_CHAT:
            raise ValidationError(
                f"В чате уже закреплено максимум сообщений ({CHAT_PINNED_MESSAGES_MAX_PER_CHAT}); открепите старые"
            )
        msg.pinned_at = _now_utc()
        msg.pinned_by_sub = user.sub
        await session.commit()
        await session.refresh(msg)

    await _load_attachments_and_hydrate_reads(session, [msg], user.sub)
    await _publish_message_updated(chat_id, msg)
    return msg


async def unpin_message(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
) -> PortalChatMessage:
    """Открепляет сообщение. Доступно любому участнику чата (не только закрепившему)."""
    await _ensure_chat_access(session, user, chat_id)
    msg = await get_visible_message_or_404(session, user, chat_id, message_id)

    if msg.pinned_at is not None:
        msg.pinned_at = None
        msg.pinned_by_sub = None
        await session.commit()
        await session.refresh(msg)

    await _load_attachments_and_hydrate_reads(session, [msg], user.sub)
    await _publish_message_updated(chat_id, msg)
    return msg


async def list_pinned_messages(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
) -> list[PortalChatMessage]:
    """Закреплённые сообщения чата, недавно закреплённые — первыми."""
    await ensure_chat_read_access(session, user, chat_id)
    stmt = (
        select(PortalChatMessage)
        .where(
            PortalChatMessage.chat_id == chat_id,
            PortalChatMessage.pinned_at.is_not(None),
            _not_hidden_for_user_sub(user.sub),
        )
        .order_by(PortalChatMessage.pinned_at.desc())
    )
    messages = list((await session.execute(stmt)).scalars().all())
    await _load_attachments_and_hydrate_reads(session, messages, user.sub)
    return messages
