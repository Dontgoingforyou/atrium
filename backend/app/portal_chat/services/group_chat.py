"""Операции над групповыми чатами (не DM): название и состав участников."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.optimistic_lock import compare_and_swap_row
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMember
from app.infrastructure.ws.managers import get_chat_manager
from app.portal_chat.services._queries import _ensure_chat_access
from app.portal_chat.services.inbox_publish import publish_chat_list_refresh
from app.schemas.auth import UserPublic
from app.services import portal_user as portal_user_svc

_CHAT_CAS_CONFLICT = "Чат изменён другим пользователем"


async def _require_group_chat(session: AsyncSession, user: UserPublic, chat_id: uuid.UUID) -> PortalChat:
    chat = await _ensure_chat_access(session, user, chat_id)
    if chat.canonical_dm_key is not None:
        raise ForbiddenError("Действие доступно только для группового чата")
    return chat


async def patch_group_chat_title(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    *,
    title: str,
    expected_version: int,
) -> PortalChat:
    chat = await _require_group_chat(session, user, chat_id)
    if chat.created_by_sub != user.sub:
        raise ForbiddenError("Менять название может только создатель чата")
    t = title.strip()
    if not t:
        raise ValidationError("Название чата не может быть пустым")
    now = _now_utc()
    new_version = await compare_and_swap_row(
        session,
        PortalChat,
        entity_id=chat_id,
        expected_version=expected_version,
        values={"title": t[:255], "updated_at": now},
        conflict_message=_CHAT_CAS_CONFLICT,
    )
    await session.commit()
    await session.refresh(chat)
    chat.version = new_version
    await get_chat_manager().publish(
        chat_id,
        {"event": "chat_meta_updated", "chat_id": str(chat_id), "title": chat.title},
    )
    return chat


async def add_member_to_group_chat(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    *,
    new_member_sub: str,
) -> PortalChatMember:
    chat = await _require_group_chat(session, user, chat_id)
    if new_member_sub == user.sub:
        raise ValidationError("Нельзя добавить себя в чат")
    known = await portal_user_svc.portal_user_subs_registered(session, {new_member_sub})
    if new_member_sub not in known:
        raise ValidationError("Пользователь не найден среди пользователей портала")
    await portal_user_svc.assert_subs_may_use_portal_chat(session, {new_member_sub})
    exists_stmt = select(PortalChatMember).where(
        PortalChatMember.chat_id == chat_id,
        PortalChatMember.user_sub == new_member_sub,
    )
    if (await session.execute(exists_stmt)).scalar_one_or_none() is not None:
        raise ConflictError("Пользователь уже в чате")
    now = _now_utc()
    row = PortalChatMember(chat_id=chat_id, user_sub=new_member_sub, joined_at=now)
    session.add(row)
    chat.updated_at = now
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError("Пользователь уже в чате") from e
    await session.refresh(row)
    await publish_chat_list_refresh(new_member_sub, chat_id, kind="group")
    await get_chat_manager().publish(
        chat_id,
        {"event": "members_updated", "chat_id": str(chat_id)},
    )
    return row


async def remove_member_from_group_chat(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    *,
    target_sub: str,
) -> None:
    chat = await _require_group_chat(session, user, chat_id)
    m_stmt = select(PortalChatMember).where(
        PortalChatMember.chat_id == chat_id,
        PortalChatMember.user_sub == target_sub,
    )
    member_row = (await session.execute(m_stmt)).scalar_one_or_none()
    if member_row is None:
        raise NotFoundError("Участник не найден в чате")

    # Создателя нельзя исключить и нельзя «выйти» самому — только остальных участников
    if target_sub == chat.created_by_sub:
        raise ForbiddenError("Создатель не может покинуть группу; исключить создателя нельзя")

    if user.sub == target_sub:
        pass  # участник (не создатель) покидает чат
    elif user.sub == chat.created_by_sub:
        pass  # создатель исключает другого
    else:
        raise ForbiddenError("Исключать участников может только создатель чата")

    await session.delete(member_row)
    chat.updated_at = _now_utc()
    await session.commit()
    await get_chat_manager().disconnect_user(chat_id, target_sub)
    await publish_chat_list_refresh(target_sub, chat_id, kind="group")
    await get_chat_manager().publish(
        chat_id,
        {"event": "members_updated", "chat_id": str(chat_id)},
    )
