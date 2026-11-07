from __future__ import annotations

import uuid
from typing import Any, BinaryIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.optimistic_lock import compare_and_swap_row
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_document_comment import (
    PortalDocumentComment,
    PortalDocumentCommentMedia,
)
from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
from app.infrastructure.ws.managers import get_document_comments_manager
from app.portal_chat.services.inbox_publish import publish_portal_notification_updates
from app.portal_collab.services import notification as notification_svc
from app.portal_documents.schemas.document_comment import (
    DocumentCommentCreate,
    DocumentCommentUpdate,
)
from app.portal_documents.services.portal_document_queries import ensure_user_can_read_document
from app.schemas.auth import UserPublic
from app.services import comment_thread as thread_svc
from app.services import rich_media as rich_media_svc

_HOST_FK = "document_id"

_COMMENT_ROW_OPTIONS = [
    selectinload(PortalDocumentComment.author_profile),
    selectinload(PortalDocumentComment.comment_media),
]
_COMMENT_MEDIA_OPTIONS = [
    *_COMMENT_ROW_OPTIONS,
    selectinload(PortalDocumentComment.replies).selectinload(PortalDocumentComment.author_profile),
    selectinload(PortalDocumentComment.replies).selectinload(PortalDocumentComment.comment_media),
]


async def _get_doc_or_404(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
) -> PortalDocument:
    """Документ для комментариев: та же RBAC-видимость, что у карточки (без корзины)."""
    return await ensure_user_can_read_document(session, user, document_id)


async def upload_comment_rich_media(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
    *,
    file_data: BinaryIO,
    file_size: int,
    content_type: str,
    original_filename: str,
) -> PortalRichMedia:
    """Загружает изображение для комментария к документу и фиксирует транзакцию."""
    media = await rich_media_svc.upload_document_rich_media(
        session,
        user,
        document_id,
        file_data=file_data,
        file_size=file_size,
        content_type=content_type,
        original_filename=original_filename,
    )
    await session.commit()
    return media


async def _reload_comment_with_media(
    session: AsyncSession,
    comment_id: uuid.UUID,
) -> PortalDocumentComment:
    """Перезагружает комментарий с replies и вложениями."""
    stmt = select(PortalDocumentComment).where(PortalDocumentComment.id == comment_id).options(*_COMMENT_MEDIA_OPTIONS)
    return (await session.execute(stmt)).scalar_one()


async def list_comments(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 200,
) -> list[PortalDocumentComment]:
    await _get_doc_or_404(session, user, document_id)
    return await thread_svc.list_top_level_comments(
        session,
        PortalDocumentComment,
        _HOST_FK,
        document_id,
        skip=skip,
        limit=limit,
        extra_options=_COMMENT_ROW_OPTIONS,
    )


async def create_comment(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
    data: DocumentCommentCreate,
) -> PortalDocumentComment:
    doc = await _get_doc_or_404(session, user, document_id)
    if data.parent_id is not None:
        await thread_svc.validate_parent_comment(
            session,
            PortalDocumentComment,
            data.parent_id,
            document_id,
            _HOST_FK,
        )
    await thread_svc.validate_comment_media_ids(
        session,
        user,
        data.media_ids or [],
        host_fk_attr=_HOST_FK,
        host_id=document_id,
    )
    now = _now_utc()
    comment = PortalDocumentComment(
        document_id=document_id,
        parent_id=data.parent_id,
        author_sub=user.sub,
        body=data.body,
        mentions=data.mentions,
        created_at=now,
        updated_at=now,
    )
    session.add(comment)
    await session.flush()
    for media_id in data.media_ids or []:
        session.add(PortalDocumentCommentMedia(comment_id=comment.id, media_id=media_id))
    notified = await notification_svc.create_document_mention_notifications(session, doc, comment, user.sub)
    await session.commit()

    await publish_portal_notification_updates(list(notified.keys()), notification_ids_by_sub=notified)
    await thread_svc.publish_thread_updated(get_document_comments_manager(), document_id)
    return await _reload_comment_with_media(session, comment.id)


async def update_comment(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
    comment_id: uuid.UUID,
    data: DocumentCommentUpdate,
) -> PortalDocumentComment:
    await _get_doc_or_404(session, user, document_id)
    comment = await thread_svc.get_comment_for_host_or_404(
        session,
        PortalDocumentComment,
        comment_id,
        document_id,
        _HOST_FK,
    )
    thread_svc.assert_author_or_admin(user, comment)
    values: dict[str, Any] = {"updated_at": _now_utc()}
    if data.body is not None:
        values["body"] = data.body
    if data.mentions is not None:
        values["mentions"] = data.mentions
    new_version = await compare_and_swap_row(
        session,
        PortalDocumentComment,
        entity_id=comment_id,
        expected_version=data.expected_version,
        values=values,
        conflict_message="Комментарий изменён другим пользователем",
    )
    await session.refresh(comment)
    comment.version = new_version
    await session.commit()
    await thread_svc.publish_thread_updated(get_document_comments_manager(), document_id)
    return await _reload_comment_with_media(session, comment_id)


async def delete_comment(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
    comment_id: uuid.UUID,
) -> None:
    await _get_doc_or_404(session, user, document_id)
    comment = await thread_svc.get_comment_for_host_or_404(
        session,
        PortalDocumentComment,
        comment_id,
        document_id,
        _HOST_FK,
    )
    thread_svc.assert_author_or_admin(user, comment, detail="Нет прав на удаление комментария")
    await session.delete(comment)
    await session.commit()
    await thread_svc.publish_thread_updated(get_document_comments_manager(), document_id)
