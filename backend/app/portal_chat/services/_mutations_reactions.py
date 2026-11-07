from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_chat import (
    PortalChatAttachment,
    PortalChatMessage,
    PortalChatMessageReaction,
)
from app.infrastructure.ws.managers import get_chat_manager
from app.portal_chat.services._queries import _ensure_chat_access, get_visible_message_or_404
from app.portal_chat.services._queries_messages import hydrate_messages_read_context, message_to_read
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


async def toggle_message_reaction(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    emoji: str,
) -> PortalChatMessage:
    await _ensure_chat_access(session, user, chat_id)
    msg = await get_visible_message_or_404(session, user, chat_id, message_id)
    # Длина (1–32) валидируется Pydantic-схемой; здесь только пост-strip проверка на пустоту
    emoji_key = emoji.strip()
    if not emoji_key:
        raise ValidationError("Некорректная реакция")

    q = select(PortalChatMessageReaction).where(
        PortalChatMessageReaction.message_id == message_id,
        PortalChatMessageReaction.user_sub == user.sub,
        PortalChatMessageReaction.emoji == emoji_key,
    )
    existing = (await session.execute(q)).scalar_one_or_none()
    if existing is not None:
        await session.delete(existing)
    else:
        locked = (
            await session.execute(select(PortalChatMessage).where(PortalChatMessage.id == message_id).with_for_update())
        ).scalar_one()
        locked.updated_at = _now_utc()
        await session.flush()
        emoji_already_present_q = (
            select(PortalChatMessageReaction.message_id)
            .where(
                PortalChatMessageReaction.message_id == message_id,
                PortalChatMessageReaction.emoji == emoji_key,
            )
            .limit(1)
        )
        emoji_already_present = (await session.execute(emoji_already_present_q)).scalar_one_or_none()
        if emoji_already_present is None:
            distinct_count_q = select(func.count(PortalChatMessageReaction.emoji.distinct())).where(
                PortalChatMessageReaction.message_id == message_id,
            )
            distinct_count = (await session.execute(distinct_count_q)).scalar_one()
            if distinct_count >= 3:
                raise ValidationError("Нельзя добавить больше 3 уникальных реакций на одно сообщение")
        session.add(
            PortalChatMessageReaction(
                message_id=message_id,
                user_sub=user.sub,
                emoji=emoji_key,
            )
        )
    await session.commit()
    await session.refresh(msg)
    att_stmt = select(PortalChatAttachment).where(
        PortalChatAttachment.message_id == message_id,
        PortalChatAttachment.chat_id == chat_id,
    )
    msg.__dict__["attachments"] = list((await session.execute(att_stmt)).scalars().all())
    await hydrate_messages_read_context(session, [msg], user.sub)

    read = message_to_read(msg)
    await get_chat_manager().publish(
        chat_id,
        {
            "event": "message_reactions_updated",
            "message_id": str(message_id),
            "reactions": [r.model_dump(mode="json") for r in read.reactions],
        },
    )
    return msg
