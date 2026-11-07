"""Галерея вложений чата: список вложений с фильтром по типу и пагинацией."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.portal_chat import PortalChatAttachment, PortalChatMessage, PortalChatMessageHidden
from app.portal_chat.services._queries import ensure_chat_read_access
from app.schemas.auth import UserPublic

AttachmentKind = Literal["media", "audio", "file"]

_KIND_PREFIXES: dict[AttachmentKind, tuple[str, ...]] = {
    "media": ("image/", "video/"),
    "audio": ("audio/",),
}


def _kind_filter(kind: AttachmentKind) -> Any:
    prefixes = _KIND_PREFIXES.get(kind)
    if prefixes is not None:
        return or_(*(PortalChatAttachment.content_type.like(f"{p}%") for p in prefixes))
    # "file" — всё, что не входит ни в одну из известных категорий
    known_prefixes = [p for prefixes in _KIND_PREFIXES.values() for p in prefixes]
    return ~or_(*(PortalChatAttachment.content_type.like(f"{p}%") for p in known_prefixes))


def _base_gallery_query(
    chat_id: uuid.UUID, user_sub: str, *, kind: AttachmentKind | None
) -> Select[tuple[PortalChatAttachment]]:
    """Базовый select вложений галереи: только привязанные к видимым (не скрытым/удалённым) сообщениям."""
    stmt = (
        select(PortalChatAttachment)
        .join(PortalChatMessage, PortalChatAttachment.message_id == PortalChatMessage.id)
        .where(
            PortalChatAttachment.chat_id == chat_id,
            PortalChatAttachment.message_id.is_not(None),
            PortalChatMessage.deleted_for_all_at.is_(None),
            ~select(PortalChatMessageHidden.message_id)
            .where(
                PortalChatMessageHidden.message_id == PortalChatMessage.id,
                PortalChatMessageHidden.user_sub == user_sub,
            )
            .exists(),
        )
    )
    if kind is not None:
        stmt = stmt.where(_kind_filter(kind))
    return stmt


async def list_chat_attachments(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    *,
    kind: AttachmentKind | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[PortalChatAttachment], int]:
    """Вложения чата (только привязанные к сообщению), новые — первыми, с общим счётчиком."""
    await ensure_chat_read_access(session, user, chat_id)

    count_stmt = select(func.count()).select_from(_base_gallery_query(chat_id, user.sub, kind=kind).subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = (
        _base_gallery_query(chat_id, user.sub, kind=kind)
        .order_by(PortalChatAttachment.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    attachments = list((await session.execute(stmt)).scalars().all())
    return attachments, total
