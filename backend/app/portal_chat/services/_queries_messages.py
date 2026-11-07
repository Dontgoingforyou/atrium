from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import exists, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.text_search import escape_ilike_pattern
from app.infrastructure.db.models.portal_chat import (
    PortalChat,
    PortalChatAttachment,
    PortalChatMember,
    PortalChatMessage,
    PortalChatMessageHidden,
    PortalChatMessageReaction,
)
from app.portal_chat.schemas.chat import (
    AttachmentRead,
    PortalChatMessageForwardFrom,
    PortalChatMessageReactionAgg,
    PortalChatMessageRead,
    PortalChatMessageReplyPreview,
)
from app.portal_chat.services._queries import (
    _exclude_orphan_non_dm_chats,
    ensure_chat_read_access,
    get_visible_message_or_404,
    list_chat_members,
    message_hidden_for_user,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

_REPLY_BODY_PREVIEW_MAX = 400


def _attachment_created_at_for_read(att: PortalChatAttachment) -> datetime:
    """Гарантирует datetime для Pydantic: в редких случаях серверный default ещё не в объекте ORM."""
    if att.created_at is not None:
        return att.created_at
    logger.warning(
        "Вложение chat без created_at в ORM (attachment_id=%s); подставляем текущее время UTC",
        att.id,
    )
    return datetime.now(UTC)


def attachment_to_read(att: PortalChatAttachment, download_url: str) -> AttachmentRead:
    """Единая точка маппинга ORM-вложения в DTO (используется роутами и гидратацией сообщений)."""
    return AttachmentRead(
        id=att.id,
        original_filename=att.original_filename,
        content_type=att.content_type,
        file_size=int(att.file_size),
        download_url=download_url,
        created_at=_attachment_created_at_for_read(att),
        voice_duration_seconds=att.voice_duration_seconds,
        voice_waveform=att.voice_waveform,
        transcript=att.voice_transcript,
        message_id=att.message_id,
    )


# ─── Маппинг ORM → DTO ────────────────────────────────────────────────────────


def _reply_preview_from_resolved(
    resolved: PortalChatMessage | None,
    *,
    quote_text: str | None = None,
    hidden_for_viewer: bool = False,
) -> PortalChatMessageReplyPreview | None:
    if resolved is None:
        return None
    deleted = resolved.deleted_for_all_at is not None or hidden_for_viewer
    if deleted:
        raw = ""
        shown_quote: str | None = None
    elif quote_text:
        raw = quote_text if len(quote_text) <= _REPLY_BODY_PREVIEW_MAX else quote_text[:_REPLY_BODY_PREVIEW_MAX] + "…"
        shown_quote = raw
    else:
        full = resolved.body or ""
        raw = full if len(full) <= _REPLY_BODY_PREVIEW_MAX else full[:_REPLY_BODY_PREVIEW_MAX] + "…"
        shown_quote = None
    return PortalChatMessageReplyPreview(
        id=resolved.id,
        author_sub=resolved.author_sub,
        body=raw,
        deleted_for_all_at=resolved.deleted_for_all_at,
        quote_text=shown_quote,
    )


def message_to_read(msg: PortalChatMessage) -> PortalChatMessageRead:
    """Публичное представление сообщения (текст скрыт, если «удалено у всех»)."""
    # Импорт умышленно локальный (не поднимать на уровень модуля): тесты мокают
    # именно app.infrastructure.storage.client.get_presigned_url (единая точка правды
    # для всех вызывающих модулей); при импорте на уровне модуля здесь появляется
    # отдельное, непропатченное имя — тесты начинают реально стучаться в MinIO.
    from app.infrastructure.storage.client import get_presigned_url

    body = "" if msg.deleted_for_all_at is not None else (msg.body or "")
    attachments: list[AttachmentRead] = []

    # Обращаемся ТОЛЬКО к тому, что уже загружено в памяти — не триггерим lazy-load
    # в синхронном контексте (async SQLAlchemy запрещает это через MissingGreenlet).
    loaded = msg.__dict__.get("attachments")
    if loaded is not None and msg.deleted_for_all_at is None:
        for att in loaded:
            try:
                ct = (att.content_type or "").split(";", 1)[0].strip().lower()
                inline_ok = ct.startswith(("image/", "video/", "audio/"))
                url = get_presigned_url(
                    att.storage_key,
                    filename=att.original_filename,
                    force_download=not inline_ok,
                )
            except Exception as exc:
                # Хранилище временно недоступно (S3Error или сетевая ошибка) —
                # URL будет пустым; клиент повторит через /download.
                logger.warning(
                    "MinIO: не удалось получить presigned URL attachment_id=%s key=%s: %s",
                    att.id,
                    att.storage_key,
                    exc,
                )
                url = ""
            attachments.append(attachment_to_read(att, str(url)))
    resolved = msg.__dict__.get("reply_to_resolved")
    reply_preview = (
        _reply_preview_from_resolved(
            resolved,
            quote_text=msg.reply_quote_text,
            hidden_for_viewer=bool(msg.__dict__.get("reply_to_hidden")),
        )
        if msg.reply_to_message_id
        else None
    )
    reactions_raw = msg.__dict__.get("reactions_agg")
    reactions: list[PortalChatMessageReactionAgg] = list(reactions_raw) if isinstance(reactions_raw, list) else []
    forwarded_from: PortalChatMessageForwardFrom | None = None
    if msg.forwarded_from_author_sub:
        forwarded_from = PortalChatMessageForwardFrom(
            author_sub=msg.forwarded_from_author_sub,
            source_message_id=msg.forwarded_from_message_id,
        )
    return PortalChatMessageRead(
        id=msg.id,
        chat_id=msg.chat_id,
        author_sub=msg.author_sub,
        body=body,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
        deleted_for_all_at=msg.deleted_for_all_at,
        attachments=attachments,
        reply_to_message_id=msg.reply_to_message_id,
        reply_quote_text=msg.reply_quote_text,
        reply_to=reply_preview,
        reactions=reactions,
        forwarded_from=forwarded_from,
        mentions=list(msg.mentions or []),
        pinned_at=msg.pinned_at,
        pinned_by_sub=msg.pinned_by_sub,
    )


def _receipt_for_message(
    msg: PortalChatMessage,
    viewer_sub: str,
    members: list[PortalChatMember],
) -> Literal["sent", "read"] | None:
    if msg.author_sub != viewer_sub:
        return None
    others = [m for m in members if m.user_sub != msg.author_sub]
    if not others:
        return "sent"
    any_read = any(o.last_read_at is not None and o.last_read_at >= msg.created_at for o in others)
    return "read" if any_read else "sent"


def message_to_read_for_viewer(
    msg: PortalChatMessage,
    viewer_sub: str,
    members: list[PortalChatMember],
) -> PortalChatMessageRead:
    base = message_to_read(msg)
    return base.model_copy(update={"receipt": _receipt_for_message(msg, viewer_sub, members)})


# ─── Батч-гидратация (reply, реакции) ─────────────────────────────────────────


async def _attach_reply_targets(
    session: AsyncSession,
    messages: list[PortalChatMessage],
    viewer_sub: str,
) -> None:
    ids = {m.reply_to_message_id for m in messages if m.reply_to_message_id}
    if not ids:
        for m in messages:
            m.__dict__["reply_to_resolved"] = None
            m.__dict__["reply_to_hidden"] = False
        return
    stmt = select(PortalChatMessage).where(PortalChatMessage.id.in_(ids))
    rows = list((await session.execute(stmt)).scalars().all())
    by_id = {r.id: r for r in rows}
    hidden_ids = {rid for rid in ids if await message_hidden_for_user(session, viewer_sub, rid)}
    for m in messages:
        rid = m.reply_to_message_id
        m.__dict__["reply_to_resolved"] = by_id.get(rid) if rid else None
        m.__dict__["reply_to_hidden"] = bool(rid and rid in hidden_ids)


async def _attach_reactions_batch(
    session: AsyncSession,
    messages: list[PortalChatMessage],
    viewer_sub: str,
) -> None:
    if not messages:
        return
    msg_ids = [m.id for m in messages]
    stmt = select(PortalChatMessageReaction).where(PortalChatMessageReaction.message_id.in_(msg_ids))
    rows = list((await session.execute(stmt)).scalars().all())
    by_mid: dict[uuid.UUID, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for r in rows:
        by_mid[r.message_id][r.emoji].add(r.user_sub)
    for m in messages:
        emojis = by_mid.get(m.id, {})
        aggs = [
            PortalChatMessageReactionAgg(
                emoji=emoji,
                count=len(users),
                reacted_by_me=viewer_sub in users,
            )
            for emoji, users in sorted(emojis.items(), key=lambda x: x[0])
        ]
        m.__dict__["reactions_agg"] = aggs


async def hydrate_messages_read_context(
    session: AsyncSession,
    messages: list[PortalChatMessage],
    viewer_sub: str,
) -> None:
    if not messages:
        return
    await _attach_reply_targets(session, messages, viewer_sub)
    await _attach_reactions_batch(session, messages, viewer_sub)


async def messages_to_read_for_viewer(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    messages: list[PortalChatMessage],
) -> list[PortalChatMessageRead]:
    # специализированный read-агрегат: сразу возвращает Pydantic DTO для конкретного читающего сценария
    members = await list_chat_members(session, chat_id)
    return [message_to_read_for_viewer(m, user.sub, members) for m in messages]


# ─── Запросы сообщений ─────────────────────────────────────────────────────────


async def get_message_readers(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
) -> list[PortalChatMember]:
    """Участники чата, прочитавшие сообщение (last_read_at >= message.created_at).

    Автор сообщения в список не включается. Доступ проверяется через ensure_chat_read_access.
    """
    await ensure_chat_read_access(session, user, chat_id)
    msg = await get_visible_message_or_404(session, user, chat_id, message_id)

    stmt = select(PortalChatMember).where(
        PortalChatMember.chat_id == chat_id,
        PortalChatMember.user_sub != msg.author_sub,
        PortalChatMember.last_read_at.isnot(None),
        PortalChatMember.last_read_at >= msg.created_at,
    )
    return list((await session.execute(stmt)).scalars().all())


async def get_message_reaction_reactors(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    emoji: str,
) -> list[PortalChatMessageReaction]:
    """Кто поставил реакцию с данным эмодзи. Чтение: участник или portal_admin.

    Набор ограничен (реакции только от members) — без пагинации, как у readers.
    """
    await ensure_chat_read_access(session, user, chat_id)
    await get_visible_message_or_404(session, user, chat_id, message_id)

    emoji_key = emoji.strip()
    if not emoji_key:
        raise ValidationError("Некорректная реакция")

    stmt = (
        select(PortalChatMessageReaction)
        .where(
            PortalChatMessageReaction.message_id == message_id,
            PortalChatMessageReaction.emoji == emoji_key,
        )
        .order_by(PortalChatMessageReaction.created_at.asc())
    )
    return list((await session.execute(stmt)).scalars().all())


def _not_hidden_for_user_sub(user_sub: str) -> Any:
    """Сообщения, не скрытые для user_sub (таблица «удалить у меня»)."""
    return not_(
        exists(
            select(1)
            .select_from(PortalChatMessageHidden)
            .where(
                PortalChatMessageHidden.message_id == PortalChatMessage.id,
                PortalChatMessageHidden.user_sub == user_sub,
            )
        )
    )


async def _load_attachments_and_hydrate_reads(
    session: AsyncSession,
    messages: list[PortalChatMessage],
    user_sub: str,
) -> None:
    if not messages:
        return
    msg_ids = [m.id for m in messages]
    att_stmt = (
        select(PortalChatAttachment)
        .where(PortalChatAttachment.message_id.in_(msg_ids))
        .order_by(PortalChatAttachment.created_at.asc())
    )
    attachments = list((await session.execute(att_stmt)).scalars().all())
    att_map: dict[uuid.UUID, list[PortalChatAttachment]] = {}
    for att in attachments:
        if att.message_id is not None:
            att_map.setdefault(att.message_id, []).append(att)
    for msg in messages:
        msg.__dict__["attachments"] = att_map.get(msg.id, [])

    await hydrate_messages_read_context(session, messages, user_sub)


async def list_messages(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 100,
    around_message_id: uuid.UUID | None = None,
) -> list[PortalChatMessage]:
    await ensure_chat_read_access(session, user, chat_id)
    hidden = _not_hidden_for_user_sub(user.sub)
    messages: list[PortalChatMessage]

    not_deleted = PortalChatMessage.deleted_for_all_at.is_(None)

    if around_message_id is not None:
        anchor_stmt = select(PortalChatMessage).where(
            PortalChatMessage.id == around_message_id,
            PortalChatMessage.chat_id == chat_id,
            hidden,
            not_deleted,
        )
        anchor = (await session.execute(anchor_stmt)).scalar_one_or_none()
        if anchor is None:
            raise NotFoundError("Сообщение не найдено")
        half_before = max(limit // 2, 1)
        half_after = limit - half_before
        stmt_before = (
            select(PortalChatMessage)
            .where(
                PortalChatMessage.chat_id == chat_id,
                PortalChatMessage.created_at < anchor.created_at,
                hidden,
                not_deleted,
            )
            .order_by(PortalChatMessage.created_at.desc())
            .limit(half_before)
        )
        before_rows = list((await session.execute(stmt_before)).scalars().all())
        before_rows.reverse()
        stmt_after = (
            select(PortalChatMessage)
            .where(
                PortalChatMessage.chat_id == chat_id,
                PortalChatMessage.created_at >= anchor.created_at,
                hidden,
                not_deleted,
            )
            .order_by(PortalChatMessage.created_at.asc())
            .limit(half_after)
        )
        after_rows = list((await session.execute(stmt_after)).scalars().all())
        messages = (before_rows + after_rows)[:limit]
        await _load_attachments_and_hydrate_reads(session, messages, user.sub)
        return messages

    stmt = (
        select(PortalChatMessage)
        .where(
            PortalChatMessage.chat_id == chat_id,
            hidden,
            not_deleted,
        )
        .order_by(PortalChatMessage.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    messages = list((await session.execute(stmt)).scalars().all())
    await _load_attachments_and_hydrate_reads(session, messages, user.sub)
    return messages


async def search_messages_for_user(
    session: AsyncSession,
    user: UserPublic,
    q: str,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[tuple[PortalChatMessage, Any]]:
    """Сообщения с подстрокой в теле в DM и групповых чатах инбокса.

    Исключаются не-DM чаты без названия (сироты), как в списке чатов. Ищем только
    чаты, где текущий пользователь — участник (админ без членства чужие группы не видит).
    """
    pl = f"%{escape_ilike_pattern(q.lower())}%"
    stmt = (
        select(PortalChatMessage, PortalChat)
        .join(PortalChat, PortalChat.id == PortalChatMessage.chat_id)
        .join(PortalChatMember, PortalChatMember.chat_id == PortalChatMessage.chat_id)
        .where(
            func.lower(PortalChatMessage.body).like(pl, escape="\\"),
            PortalChatMessage.deleted_for_all_at.is_(None),
            _not_hidden_for_user_sub(user.sub),
            _exclude_orphan_non_dm_chats(),
            PortalChatMember.user_sub == user.sub,
        )
        .order_by(PortalChatMessage.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [(row[0], row[1]) for row in rows]
