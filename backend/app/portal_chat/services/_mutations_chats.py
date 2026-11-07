"""Мутирующие операции с чатами: создание, DM, пометка прочитанным."""

from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMember
from app.infrastructure.ws.managers import get_chat_manager
from app.portal_chat.schemas.chat import PortalChatCreate
from app.portal_chat.services._queries import _ensure_chat_access
from app.portal_chat.services.inbox_publish import publish_chat_list_refresh
from app.schemas.auth import UserPublic
from app.services import portal_user as portal_user_svc


async def create_chat(session: AsyncSession, user: UserPublic, data: PortalChatCreate) -> PortalChat:
    members_set = {user.sub, *data.member_subs}
    if len(members_set) < 2:
        raise ValidationError("Укажите хотя бы одного участника чата (кроме себя)")
    title_stripped = (data.title or "").strip()
    if not title_stripped:
        raise ValidationError("Укажите непустое название группового чата")
    others = members_set - {user.sub}
    registered = await portal_user_svc.portal_user_subs_registered(session, others)
    missing = others - registered
    if missing:
        raise ValidationError("Неизвестные пользователи: " + ", ".join(sorted(missing)[:5]))
    await portal_user_svc.assert_subs_may_use_portal_chat(session, others)

    now = _now_utc()
    chat = PortalChat(
        title=title_stripped[:255],
        created_by_sub=user.sub,
        created_at=now,
        updated_at=now,
    )
    session.add(chat)
    await session.flush()

    for sub in members_set:
        session.add(PortalChatMember(chat_id=chat.id, user_sub=sub, joined_at=now))

    await session.commit()
    await session.refresh(chat)

    for sub in members_set:
        if sub != user.sub:
            await publish_chat_list_refresh(sub, chat.id, kind="group")

    return chat


async def get_or_create_direct_chat(
    session: AsyncSession,
    user: UserPublic,
    other_user_sub: str,
) -> PortalChat:
    """Находит или создаёт прямой чат (DM) между двумя пользователями.

    Идемпотентен и безопасен при конкурентных вызовах: поиск ведётся
    по canonical_dm_key (UNIQUE-индекс в БД). При гонке двух параллельных
    запросов второй получит IntegrityError, откатится и вернёт уже
    созданный чат.

    canonical_dm_key = "{min_sub}|{max_sub}" (алфавитный порядок),
    что обеспечивает одинаковый ключ независимо от того, кто инициатор.
    """
    key = "|".join(sorted([user.sub, other_user_sub]))
    lookup = select(PortalChat).where(PortalChat.canonical_dm_key == key)

    existing = (await session.execute(lookup)).scalars().first()
    if existing is not None:
        return existing

    await portal_user_svc.assert_subs_may_use_portal_chat(session, {other_user_sub})

    now = _now_utc()
    chat = PortalChat(
        title=None,
        created_by_sub=user.sub,
        created_at=now,
        updated_at=now,
        canonical_dm_key=key,
    )
    session.add(chat)
    try:
        await session.flush()
        for sub in {user.sub, other_user_sub}:
            session.add(PortalChatMember(chat_id=chat.id, user_sub=sub, joined_at=now))
        await session.commit()
        await session.refresh(chat)
        return chat
    except IntegrityError:
        # Конкурентный запрос уже создал чат — откатываемся и делаем повторный поиск.
        await session.rollback()
        result = (await session.execute(lookup)).scalars().first()
        if result is None:
            raise  # неожиданная ошибка целостности
        return result


async def mark_chat_read(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
) -> None:
    """Выставить last_read_at = now() для текущего пользователя в чате."""
    await _ensure_chat_access(session, user, chat_id)
    stmt = (
        update(PortalChatMember)
        .where(
            PortalChatMember.chat_id == chat_id,
            PortalChatMember.user_sub == user.sub,
        )
        .values(last_read_at=_now_utc())
    )
    await session.execute(stmt)
    await session.commit()

    await get_chat_manager().publish(
        chat_id,
        {"event": "read_state_updated"},
    )
