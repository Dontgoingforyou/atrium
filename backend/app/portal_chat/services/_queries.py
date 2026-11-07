"""Читающие функции portal_chat: чаты, доступ, вспомогательные SQL-фильтры.

Вспомогательная логика доступа (_ensure_chat_access) также здесь, чтобы
мутации могли импортировать её без кольцевой зависимости.

Запросы по сообщениям — в _queries_messages.py.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import and_, exists, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_chat import (
    PortalChat,
    PortalChatMember,
    PortalChatMessage,
    PortalChatMessageHidden,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


# ─── Вспомогательные запросы ──────────────────────────────────────────────────


async def message_hidden_for_user(session: AsyncSession, user_sub: str, message_id: uuid.UUID) -> bool:
    q = select(1).where(
        PortalChatMessageHidden.user_sub == user_sub,
        PortalChatMessageHidden.message_id == message_id,
    )
    return (await session.execute(q)).scalar_one_or_none() is not None


async def list_chat_members(session: AsyncSession, chat_id: uuid.UUID) -> list[PortalChatMember]:
    q = select(PortalChatMember).where(PortalChatMember.chat_id == chat_id)
    return list((await session.execute(q)).scalars().all())


# ─── SQL-фильтры ──────────────────────────────────────────────────────────────


def _exclude_orphan_non_dm_chats() -> Any:
    """SQL: не-DM без названия — сироты (например, из-за незавершённого создания)."""
    return not_(
        and_(
            PortalChat.canonical_dm_key.is_(None),
            or_(PortalChat.title.is_(None), PortalChat.title == ""),
        )
    )


def _is_orphan_non_dm_group_chat_row(chat: PortalChat) -> bool:
    """Соответствует фильтру `_exclude_orphan_non_dm_chats` для проверки доступа."""
    if chat.canonical_dm_key is not None:
        return False
    if chat.title is None:
        return True
    return chat.title.strip() == ""


# ─── Доступ ───────────────────────────────────────────────────────────────────


async def _user_member_of_chat(session: AsyncSession, chat_id: uuid.UUID, user_sub: str) -> bool:
    q = select(PortalChatMember).where(
        PortalChatMember.chat_id == chat_id,
        PortalChatMember.user_sub == user_sub,
    )
    return (await session.execute(q)).scalar_one_or_none() is not None


async def user_is_chat_member(session: AsyncSession, chat_id: uuid.UUID, user_sub: str) -> bool:
    """Публичная проверка членства пользователя в чате."""
    return await _user_member_of_chat(session, chat_id, user_sub)


async def _load_chat_or_404(session: AsyncSession, chat_id: uuid.UUID) -> PortalChat:
    chat = await session.get(PortalChat, chat_id)
    if chat is None or _is_orphan_non_dm_group_chat_row(chat):
        raise NotFoundError("Чат не найден")
    return chat


def _deny_chat_access(user: UserPublic, chat_id: uuid.UUID) -> None:
    logger.warning(
        "Отказ в доступе к чату: user_sub=%s chat_id=%s",
        user.sub,
        chat_id,
    )
    raise ForbiddenError("Нет доступа к чату")


async def ensure_chat_read_access(session: AsyncSession, user: UserPublic, chat_id: uuid.UUID) -> PortalChat:
    """Чтение: участник или portal_admin (история, галерея, download, WS-слушатель)."""
    chat = await _load_chat_or_404(session, chat_id)
    if user.is_portal_admin:
        return chat
    if not await _user_member_of_chat(session, chat_id, user.sub):
        _deny_chat_access(user, chat_id)
    return chat


async def ensure_chat_write_access(session: AsyncSession, user: UserPublic, chat_id: uuid.UUID) -> PortalChat:
    """Мутации и ephemeral WS: только членство, admin без членства — 403."""
    chat = await _load_chat_or_404(session, chat_id)
    if not await _user_member_of_chat(session, chat_id, user.sub):
        _deny_chat_access(user, chat_id)
    return chat


async def _ensure_chat_access(session: AsyncSession, user: UserPublic, chat_id: uuid.UUID) -> PortalChat:
    """Алиас записи (мутации)."""
    return await ensure_chat_write_access(session, user, chat_id)


async def ensure_chat_access(session: AsyncSession, user: UserPublic, chat_id: uuid.UUID) -> PortalChat:
    """Публичный алиас записи (upload, mark_read и т.п.). Для чтения — ``ensure_chat_read_access``."""
    return await ensure_chat_write_access(session, user, chat_id)


async def get_visible_message_or_404(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
) -> PortalChatMessage:
    """Сообщение в чате, не скрытое у viewer («удалить у меня» → 404 как в ленте)."""
    msg = await session.get(PortalChatMessage, message_id)
    if msg is None or msg.chat_id != chat_id:
        raise NotFoundError("Сообщение не найдено")
    if await message_hidden_for_user(session, user.sub, message_id):
        raise NotFoundError("Сообщение не найдено")
    return msg


# ─── Запросы чтения (чаты) ────────────────────────────────────────────────────


async def list_chats_for_user(
    session: AsyncSession,
    user: UserPublic,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalChat]:
    stmt = (
        select(PortalChat)
        .join(PortalChatMember, PortalChatMember.chat_id == PortalChat.id)
        .where(
            PortalChatMember.user_sub == user.sub,
            _exclude_orphan_non_dm_chats(),
        )
        .order_by(PortalChat.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list((await session.execute(stmt)).scalars().unique().all())


async def user_can_access_message(session: AsyncSession, user: UserPublic, message_id: uuid.UUID) -> bool:
    msg = await session.get(PortalChatMessage, message_id)
    if msg is None:
        return False
    chat = await session.get(PortalChat, msg.chat_id)
    if chat is None:
        return False
    if user.is_portal_admin:
        return True
    return await _user_member_of_chat(session, msg.chat_id, user.sub)


async def get_batch_unread_counts(
    session: AsyncSession,
    user_sub: str,
    chat_ids: list[uuid.UUID],
) -> dict[uuid.UUID, int]:
    """Батч-подсчёт непрочитанных сообщений по чатам за один запрос.

    Непрочитанные = сообщения не от текущего пользователя,
    созданные позже last_read_at (или все, если last_read_at IS NULL).
    """
    if not chat_ids:
        return {}
    stmt = (
        select(
            PortalChatMember.chat_id,
            func.count(PortalChatMessage.id).label("unread_count"),
        )
        .select_from(PortalChatMember)
        .join(PortalChat, PortalChat.id == PortalChatMember.chat_id)
        .outerjoin(
            PortalChatMessage,
            and_(
                PortalChatMessage.chat_id == PortalChatMember.chat_id,
                PortalChatMessage.author_sub != PortalChatMember.user_sub,
                PortalChatMessage.deleted_for_all_at.is_(None),
                not_(
                    exists(
                        select(1)
                        .select_from(PortalChatMessageHidden)
                        .where(
                            PortalChatMessageHidden.message_id == PortalChatMessage.id,
                            PortalChatMessageHidden.user_sub == PortalChatMember.user_sub,
                        )
                    )
                ),
                # NULL last_read_at означает «ни разу не читал» — все сообщения непрочитаны
                PortalChatMember.last_read_at.is_(None)
                | (PortalChatMessage.created_at > PortalChatMember.last_read_at),
            ),
        )
        .where(
            PortalChatMember.user_sub == user_sub,
            PortalChatMember.chat_id.in_(chat_ids),
        )
        .group_by(PortalChatMember.chat_id)
    )
    rows = (await session.execute(stmt)).all()
    return {row.chat_id: row.unread_count for row in rows}


async def get_unread_counts_for_chat_members(
    session: AsyncSession,
    chat_id: uuid.UUID,
    user_subs: list[str],
) -> dict[str, int]:
    """Батч-подсчёт непрочитанных для нескольких участников одного чата за один запрос.

    Возвращает словарь {user_sub: unread_count}. Инверсия get_batch_unread_counts:
    один чат — много пользователей (используется при рассылке Web Push).
    """
    if not user_subs:
        return {}
    stmt = (
        select(
            PortalChatMember.user_sub,
            func.count(PortalChatMessage.id).label("unread_count"),
        )
        .select_from(PortalChatMember)
        .join(PortalChat, PortalChat.id == PortalChatMember.chat_id)
        .outerjoin(
            PortalChatMessage,
            and_(
                PortalChatMessage.chat_id == PortalChatMember.chat_id,
                PortalChatMessage.author_sub != PortalChatMember.user_sub,
                PortalChatMessage.deleted_for_all_at.is_(None),
                not_(
                    exists(
                        select(1)
                        .select_from(PortalChatMessageHidden)
                        .where(
                            PortalChatMessageHidden.message_id == PortalChatMessage.id,
                            PortalChatMessageHidden.user_sub == PortalChatMember.user_sub,
                        )
                    )
                ),
                PortalChatMember.last_read_at.is_(None)
                | (PortalChatMessage.created_at > PortalChatMember.last_read_at),
            ),
        )
        .where(
            PortalChatMember.chat_id == chat_id,
            PortalChatMember.user_sub.in_(user_subs),
        )
        .group_by(PortalChatMember.user_sub)
    )
    rows = (await session.execute(stmt)).all()
    return {row.user_sub: row.unread_count for row in rows}
