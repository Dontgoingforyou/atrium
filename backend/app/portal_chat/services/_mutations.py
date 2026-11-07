"""Мутирующие операции portal_chat: создание/изменение/удаление сообщений.

Чат-мутации (create_chat, get_or_create_direct_chat, mark_chat_read) — _mutations_chats.py
Реакции — _mutations_reactions.py
Пересылка — _mutations_forward.py
"""

from __future__ import annotations

import logging
import uuid

from minio.error import S3Error
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ForbiddenError,
    NotFoundError,
    StorageUnavailableError,
    ValidationError,
)
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_chat import (
    PortalChatAttachment,
    PortalChatMessage,
    PortalChatMessageHidden,
)
from app.infrastructure.storage.client import async_delete_object
from app.infrastructure.ws.managers import get_chat_manager
from app.portal_chat.schemas.chat import PortalChatMessageCreate, PortalChatMessageUpdate
from app.portal_chat.services._queries import (
    _ensure_chat_access,
    list_chat_members,
    message_hidden_for_user,
)
from app.portal_chat.services._queries_messages import (
    _load_attachments_and_hydrate_reads,
    hydrate_messages_read_context,
    message_to_read,
)
from app.portal_chat.services.attachment import link_attachments_to_message
from app.portal_chat.services.inbox_preview import build_inbox_preview_text
from app.portal_chat.services.inbox_publish import (
    InboxChatKind,
    publish_chat_inbox_withdrawals,
    publish_chat_list_refresh,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


def _normalize_in_chat_mentions(
    raw: list[str],
    *,
    member_subs: set[str],
    author_sub: str,
) -> list[str]:
    """Только участники чата, не автор; порядок сохраняем, без дублей."""
    out: list[str] = []
    seen: set[str] = set()
    for sub in raw:
        if sub in member_subs and sub != author_sub and sub not in seen:
            seen.add(sub)
            out.append(sub)
    return out


async def post_message(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    data: PortalChatMessageCreate,
) -> PortalChatMessage:
    chat = await _ensure_chat_access(session, user, chat_id)
    members = await list_chat_members(session, chat_id)
    member_subs = {m.user_sub for m in members}
    mentions_norm = _normalize_in_chat_mentions(
        data.mentions,
        member_subs=member_subs,
        author_sub=user.sub,
    )
    reply_id = data.reply_to_message_id
    reply_quote: str | None = None
    if reply_id is not None:
        ref = await session.get(PortalChatMessage, reply_id)
        if ref is None or ref.chat_id != chat_id:
            raise ValidationError("Цитируемое сообщение не найдено")
        if ref.deleted_for_all_at is not None:
            raise ValidationError("Нельзя ответить на удалённое сообщение")
        if await message_hidden_for_user(session, user.sub, reply_id):
            raise ValidationError("Нельзя ответить на это сообщение")
        if data.reply_quote_text is not None:
            quote = data.reply_quote_text.strip()
            if quote:
                # Точное вхождение фрагмента в тело целевого сообщения (как выделил пользователь).
                if quote not in (ref.body or ""):
                    raise ValidationError("Цитата не является фрагментом исходного сообщения")
                reply_quote = quote
    elif data.reply_quote_text is not None:
        raise ValidationError("Цитата допустима только вместе с reply_to_message_id")
    msg = PortalChatMessage(
        chat_id=chat_id,
        author_sub=user.sub,
        body=data.body,
        created_at=_now_utc(),
        reply_to_message_id=reply_id,
        reply_quote_text=reply_quote,
        mentions=mentions_norm,
    )
    session.add(msg)
    chat.updated_at = _now_utc()
    await session.flush()  # получаем msg.id до привязки вложений

    if data.attachment_ids:
        linked = await link_attachments_to_message(
            session,
            attachment_ids=data.attachment_ids,
            message_id=msg.id,
            chat_id=chat_id,
            uploader_sub=user.sub,
        )
    else:
        linked = []

    await session.commit()
    await session.refresh(msg)

    # Записываем в __dict__ напрямую — минуя SQLAlchemy-инструментацию,
    # чтобы не триггерить lazy-load в синхронном контексте.
    msg.__dict__["attachments"] = linked
    await hydrate_messages_read_context(session, [msg], user.sub)

    # Публикуем после коммита (envelope: event + message)
    read = message_to_read(msg)
    await get_chat_manager().publish(
        chat_id,
        {"event": "message_created", "message": read.model_dump(mode="json")},
    )

    inbox_kind: InboxChatKind = "dm" if chat.canonical_dm_key is not None else "group"
    preview = build_inbox_preview_text(
        body=msg.body or "",
        attachment_content_types=[a.content_type for a in linked],
    )
    title_stripped = (chat.title or "").strip()
    chat_title = title_stripped or None
    is_direct = chat.canonical_dm_key is not None
    for m in members:
        if m.user_sub != user.sub:
            await publish_chat_list_refresh(
                m.user_sub,
                chat_id,
                kind=inbox_kind,
                author_sub=user.sub,
                preview_text=preview,
                is_direct=is_direct,
                chat_title=chat_title,
                recipient_mentioned=m.user_sub in mentions_norm,
                message_id=msg.id,
            )

    return msg


async def update_message(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    data: PortalChatMessageUpdate,
) -> PortalChatMessage:
    chat = await _ensure_chat_access(session, user, chat_id)
    msg = await session.get(PortalChatMessage, message_id)
    if msg is None or msg.chat_id != chat_id:
        raise NotFoundError("Сообщение не найдено")
    if msg.author_sub != user.sub:
        raise ForbiddenError("Нельзя редактировать чужое сообщение")
    if msg.deleted_for_all_at is not None:
        raise ForbiddenError("Сообщение удалено")
    now = _now_utc()
    msg.body = data.body
    msg.updated_at = now
    chat.updated_at = now
    await session.commit()
    await session.refresh(msg)
    await _load_attachments_and_hydrate_reads(session, [msg], user.sub)

    read = message_to_read(msg)
    await get_chat_manager().publish(
        chat_id,
        {"event": "message_updated", "message": read.model_dump(mode="json")},
    )
    return msg


async def delete_message_for_user(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
) -> None:
    """Скрыть сообщение только у текущего пользователя. Идемпотентно, без WebSocket."""
    await _ensure_chat_access(session, user, chat_id)
    msg = await session.get(PortalChatMessage, message_id)
    if msg is None or msg.chat_id != chat_id:
        raise NotFoundError("Сообщение не найдено")
    q = select(PortalChatMessageHidden).where(
        PortalChatMessageHidden.user_sub == user.sub,
        PortalChatMessageHidden.message_id == message_id,
    )
    if (await session.execute(q)).scalar_one_or_none() is not None:
        return
    session.add(
        PortalChatMessageHidden(
            user_sub=user.sub,
            message_id=message_id,
            chat_id=chat_id,
            created_at=_now_utc(),
        )
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()


async def _purge_attachments_for_message(
    session: AsyncSession,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
) -> None:
    """Удаляет объекты в MinIO и строки ``portal_chat_attachment`` для сообщения.

    Порядок: сначала MinIO для каждого ключа (при сбое хранилища строки БД не
    фиксируются выше по стеку — пользователь может повторить; уже удалённые
    ключи при повторе дают NoSuchKey и игнорируются в ``delete_object``), затем
    удаление строк вложений в текущей сессии.
    """
    stmt = select(PortalChatAttachment).where(
        PortalChatAttachment.chat_id == chat_id,
        PortalChatAttachment.message_id == message_id,
    )
    attachments = list((await session.execute(stmt)).scalars().all())
    for att in attachments:
        try:
            await async_delete_object(att.storage_key)
        except S3Error as exc:
            logger.exception(
                "Не удалось удалить вложение из MinIO: storage_key=%s",
                att.storage_key,
            )
            raise StorageUnavailableError() from exc
    for att in attachments:
        await session.delete(att)


async def delete_message_for_all(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
) -> PortalChatMessage:
    """Пометить сообщение удалённым для всех; только автор."""
    chat = await _ensure_chat_access(session, user, chat_id)
    msg = await session.get(PortalChatMessage, message_id)
    if msg is None or msg.chat_id != chat_id:
        raise NotFoundError("Сообщение не найдено")
    if msg.author_sub != user.sub:
        raise ForbiddenError("Удалить у всех может только автор")
    if msg.deleted_for_all_at is not None:
        return msg

    members = await list_chat_members(session, chat_id)
    await _purge_attachments_for_message(session, chat_id, message_id)

    now = _now_utc()
    msg.body = ""
    msg.deleted_for_all_at = now
    msg.updated_at = now
    chat.updated_at = now
    await session.commit()
    await session.refresh(msg)
    msg.__dict__["attachments"] = []
    await hydrate_messages_read_context(session, [msg], user.sub)

    read = message_to_read(msg)
    await get_chat_manager().publish(
        chat_id,
        {"event": "message_deleted", "message": read.model_dump(mode="json")},
    )
    others = [m.user_sub for m in members if m.user_sub != user.sub]
    await publish_chat_inbox_withdrawals(others, chat_id, message_id)
    return msg
