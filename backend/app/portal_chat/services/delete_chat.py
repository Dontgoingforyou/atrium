from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.portal_search_constants import PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatAttachment, PortalChatMessage
from app.infrastructure.storage.client import async_delete_objects
from app.infrastructure.ws.managers import get_chat_manager
from app.portal_chat.services._queries import list_chat_members, user_is_chat_member
from app.portal_chat.services.inbox_publish import InboxChatKind, publish_chat_list_refresh
from app.portal_search.services.embedding import delete_embeddings_batch
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


async def delete_entire_chat(session: AsyncSession, user: UserPublic, chat_id: uuid.UUID) -> None:
    chat = await session.get(PortalChat, chat_id)
    if chat is None or not await user_is_chat_member(session, chat_id, user.sub):
        raise NotFoundError("Чат не найден")

    if chat.canonical_dm_key is not None:
        pass  # DM: любой участник (уже проверен доступ)
    else:
        if chat.created_by_sub != user.sub:
            raise ForbiddenError("Удалить групповой чат может только создатель")

    members = await list_chat_members(session, chat_id)
    member_subs = [m.user_sub for m in members]
    is_dm = chat.canonical_dm_key is not None

    att_stmt = select(PortalChatAttachment.storage_key).where(PortalChatAttachment.chat_id == chat_id)
    storage_keys = list((await session.execute(att_stmt)).scalars().all())
    if chat.avatar_storage_key and chat.avatar_storage_key not in storage_keys:
        storage_keys.append(chat.avatar_storage_key)

    message_ids = list(
        (await session.scalars(select(PortalChatMessage.id).where(PortalChatMessage.chat_id == chat_id))).all()
    )

    await session.delete(chat)
    await session.commit()

    if storage_keys:
        try:
            await async_delete_objects(storage_keys)
        except Exception:
            logger.exception(
                "MinIO: не удалось удалить объекты удалённого чата chat_id=%s keys=%d",
                chat_id,
                len(storage_keys),
            )

    manager = get_chat_manager()
    for sub in member_subs:
        await manager.disconnect_user(chat_id, sub)

    # Публикуем после коммита — как и остальные мутации модуля (см. _mutations.py):
    # клиент не должен получить "chat_deleted" раньше, чем удаление реально зафиксировано.
    await manager.publish(
        chat_id,
        {"event": "chat_deleted", "chat_id": str(chat_id)},
    )

    await delete_embeddings_batch(
        session,
        PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE,
        [str(mid) for mid in message_ids],
    )

    kind: InboxChatKind = "dm" if is_dm else "group"
    for sub in member_subs:
        await publish_chat_list_refresh(sub, chat_id, kind=kind)
