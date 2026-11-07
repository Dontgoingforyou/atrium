from __future__ import annotations

import uuid
from typing import cast
from urllib.parse import quote

from sqlalchemy import exists, not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.infrastructure.db.models.portal_chat import (
    PortalChat,
    PortalChatMessage,
    PortalChatMessageHidden,
)
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_telegram.services.telegram_text_preview import (
    attachment_preview_label,
    profile_display,
    telegram_plain_preview,
)


async def _resolve_dm_peer_title(db: AsyncSession, other_sub: str) -> str:
    prof = await db.get(PortalUserProfile, other_sub)
    d = profile_display(prof, fallback_sub=other_sub)
    return d if d else other_sub


async def source_message_visible_for_recipient(
    db: AsyncSession,
    *,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    recipient_sub: str,
) -> bool:
    """Сообщение ещё можно показать: не удалено для всех и не скрыто у получателя."""
    hidden_exists = exists(
        select(1).where(
            PortalChatMessageHidden.message_id == message_id,
            PortalChatMessageHidden.user_sub == recipient_sub,
        )
    )
    stmt = select(PortalChatMessage.id).where(
        PortalChatMessage.id == message_id,
        PortalChatMessage.chat_id == chat_id,
        PortalChatMessage.deleted_for_all_at.is_(None),
        not_(hidden_exists),
    )
    return (await db.scalar(stmt)) is not None


async def _latest_visible_message_for_recipient(
    db: AsyncSession,
    chat_id: uuid.UUID,
    recipient_sub: str,
) -> PortalChatMessage | None:
    hidden_exists = exists(
        select(1).where(
            PortalChatMessageHidden.message_id == PortalChatMessage.id,
            PortalChatMessageHidden.user_sub == recipient_sub,
        )
    )
    stmt = (
        select(PortalChatMessage)
        .where(
            PortalChatMessage.chat_id == chat_id,
            PortalChatMessage.deleted_for_all_at.is_(None),
            not_(hidden_exists),
        )
        .order_by(PortalChatMessage.created_at.desc())
        .limit(1)
        .options(selectinload(PortalChatMessage.attachments))
    )
    return cast(PortalChatMessage | None, await db.scalar(stmt))


async def format_chat_inbox_telegram(
    db: AsyncSession,
    *,
    recipient_sub: str,
    chat_id: uuid.UUID,
    kind: str,
    settings: Settings,
) -> tuple[str, str] | None:
    """Текст и URL для кнопки.

    None — чат не найден или пользователь не участник.
    """
    stmt = (
        select(PortalChat)
        .where(PortalChat.id == chat_id)
        .options(
            selectinload(PortalChat.members),
        )
    )
    chat = await db.scalar(stmt)
    if chat is None:
        return None
    member_subs = {m.user_sub for m in chat.members}
    if recipient_sub not in member_subs:
        return None

    if chat.title and chat.title.strip():
        title = chat.title.strip()
    elif chat.canonical_dm_key is not None:
        others = [m.user_sub for m in chat.members if m.user_sub != recipient_sub]
        title = await _resolve_dm_peer_title(db, others[0]) if others else "Личный чат"
    else:
        title = "Чат"

    base = settings.portal_public_url.strip().rstrip("/")
    path = f"/chats?chat={quote(str(chat_id), safe='')}"
    link = f"{base}{path}"
    kind_label = "личном чате" if kind == "dm" else "групповом чате"
    header_emoji = "💬" if kind == "dm" else "👥"
    lines = [
        f"{header_emoji} Сообщение!",
        "",
        f"Новое сообщение или обновление в {kind_label}: «{title}»",
    ]

    last_msg = await _latest_visible_message_for_recipient(db, chat_id, recipient_sub)
    if last_msg is not None:
        if kind == "group":
            author_prof = await db.get(PortalUserProfile, last_msg.author_sub)
            author_label = profile_display(
                author_prof,
                fallback_sub=last_msg.author_sub,
            )
            lines.append("")
            lines.append(f"От: {author_label}")
        raw_body = (last_msg.body or "").strip()
        n_att = len(last_msg.attachments or [])
        if raw_body:
            lines.append("")
            lines.append(f"«{telegram_plain_preview(raw_body)}»")
        elif n_att:
            lines.append("")
            lines.append(attachment_preview_label(n_att))

    return ("\n".join(lines), link)
