from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_chat import PortalChatAttachment, PortalChatMessage
from app.infrastructure.storage.client import async_copy_object_to_new_key
from app.infrastructure.ws.managers import get_chat_manager
from app.portal_chat.services._queries import _ensure_chat_access, list_chat_members, message_hidden_for_user
from app.portal_chat.services._queries_messages import hydrate_messages_read_context, message_to_read
from app.portal_chat.services.inbox_preview import build_inbox_preview_text
from app.portal_chat.services.inbox_publish import InboxChatKind, publish_chat_list_refresh
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


async def forward_chat_message(
    session: AsyncSession,
    user: UserPublic,
    target_chat_id: uuid.UUID,
    from_chat_id: uuid.UUID,
    message_id: uuid.UUID,
) -> PortalChatMessage:
    """Копирует сообщение в другой чат (текст и вложения); вложения дублируются в MinIO."""
    if target_chat_id == from_chat_id:
        raise ValidationError("Выберите другой чат для пересылки")

    target_chat = await _ensure_chat_access(session, user, target_chat_id)
    await _ensure_chat_access(session, user, from_chat_id)

    src = await session.get(PortalChatMessage, message_id)
    if src is None or src.chat_id != from_chat_id:
        raise NotFoundError("Сообщение не найдено")
    if src.deleted_for_all_at is not None:
        raise ValidationError("Нельзя переслать удалённое сообщение")
    if await message_hidden_for_user(session, user.sub, message_id):
        raise ValidationError("Нельзя переслать это сообщение")

    snap_author = src.forwarded_from_author_sub if src.forwarded_from_author_sub else src.author_sub

    att_stmt = select(PortalChatAttachment).where(
        PortalChatAttachment.message_id == message_id,
        PortalChatAttachment.chat_id == from_chat_id,
    )
    src_atts = list((await session.execute(att_stmt)).scalars().all())

    now = _now_utc()
    new_msg = PortalChatMessage(
        chat_id=target_chat_id,
        author_sub=user.sub,
        body=src.body or "",
        created_at=now,
        reply_to_message_id=None,
        forwarded_from_message_id=src.id,
        forwarded_from_author_sub=snap_author,
        mentions=[],
    )
    session.add(new_msg)
    target_chat.updated_at = now
    await session.flush()

    for att in src_atts:
        new_key = await async_copy_object_to_new_key(att.storage_key)
        session.add(
            PortalChatAttachment(
                chat_id=target_chat_id,
                message_id=new_msg.id,
                uploader_sub=user.sub,
                original_filename=att.original_filename,
                content_type=att.content_type,
                file_size=att.file_size,
                storage_key=new_key,
            )
        )

    await session.commit()
    await session.refresh(new_msg)

    att_reload = select(PortalChatAttachment).where(
        PortalChatAttachment.message_id == new_msg.id,
        PortalChatAttachment.chat_id == target_chat_id,
    )
    linked = list((await session.execute(att_reload)).scalars().all())
    new_msg.__dict__["attachments"] = linked
    await hydrate_messages_read_context(session, [new_msg], user.sub)

    read = message_to_read(new_msg)
    await get_chat_manager().publish(
        target_chat_id,
        {"event": "message_created", "message": read.model_dump(mode="json")},
    )

    inbox_kind: InboxChatKind = "dm" if target_chat.canonical_dm_key is not None else "group"
    preview = build_inbox_preview_text(
        body=new_msg.body or "",
        attachment_content_types=[a.content_type for a in linked],
    )
    title_stripped = (target_chat.title or "").strip()
    chat_title = title_stripped or None
    is_direct = target_chat.canonical_dm_key is not None
    members = await list_chat_members(session, target_chat_id)
    for m in members:
        if m.user_sub != user.sub:
            await publish_chat_list_refresh(
                m.user_sub,
                target_chat_id,
                kind=inbox_kind,
                author_sub=user.sub,
                preview_text=preview,
                is_direct=is_direct,
                chat_title=chat_title,
            )

    return new_msg
