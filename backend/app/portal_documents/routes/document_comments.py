from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, File, Query, UploadFile, WebSocket, WebSocketDisconnect, status

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.api.deps_rbac import AccessibleDocument
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_document_comment import PortalDocumentComment
from app.infrastructure.ws import tickets as ws_ticket_svc
from app.infrastructure.ws.keepalive import is_pong, ws_keepalive
from app.infrastructure.ws.managers import get_document_comments_manager
from app.portal_chat.schemas.chat import PortalChatWsTicketRead
from app.portal_documents.schemas.document_comment import (
    DocumentCommentCreate,
    DocumentCommentRead,
    DocumentCommentUpdate,
)
from app.portal_documents.services import document_comment as comment_svc
from app.portal_documents.services.portal_document_queries import ensure_user_can_read_document
from app.schemas.auth import UserPublic
from app.schemas.rich_media import RichMediaRead
from app.services import rich_media as rich_media_svc
from app.services.file_upload_validation import open_upload_stream

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Документы"])
ws_router = APIRouter(tags=["Документы"])


def _author_display_name(comment: PortalDocumentComment) -> str | None:
    profile = comment.author_profile
    if profile is None:
        return None
    return profile.full_name or profile.email or profile.username or None


def _comment_to_read(comment: PortalDocumentComment) -> DocumentCommentRead:
    """Строит DocumentCommentRead с presigned URL для вложений (рекурсивно для replies)."""
    return DocumentCommentRead(
        id=comment.id,
        document_id=comment.document_id,
        parent_id=comment.parent_id,
        author_sub=comment.author_sub,
        author_display_name=_author_display_name(comment),
        body=comment.body,
        mentions=list(comment.mentions or []),
        version=getattr(comment, "version", 1) or 1,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        replies=[_comment_to_read(r) for r in (comment.replies or [])],
        media=[rich_media_svc.rich_media_to_read(rm) for rm in comment.media],
    )


@router.post(
    "/documents/{document_id}/comments/ws-ticket",
    summary="Тикет WebSocket треда комментариев к документу",
    response_model=PortalChatWsTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_comments_ws_ticket(
    doc: AccessibleDocument,
    user: CurrentUser,
) -> PortalChatWsTicketRead:
    t = await ws_ticket_svc.issue_document_comments_ws_ticket(doc.id, user)
    return PortalChatWsTicketRead(ticket=t)


@ws_router.websocket("/documents/{document_id}/comments/ws")
async def document_comments_websocket(
    websocket: WebSocket,
    document_id: uuid.UUID,
    db: DbSession,
    ticket: str = Query(..., min_length=8, description="Одноразовый тикет из POST .../comments/ws-ticket"),
) -> None:
    parsed = await ws_ticket_svc.consume_document_comments_ws_ticket(ticket)
    if parsed is None:
        await websocket.close(code=4001)
        return
    did, user = parsed
    if did != document_id:
        await websocket.close(code=4001)
        return
    try:
        u = user if isinstance(user, UserPublic) else UserPublic.model_validate(user)
        await ensure_user_can_read_document(db, u, document_id)
    except (NotFoundError, ForbiddenError):
        await websocket.close(code=4001)
        return

    manager = get_document_comments_manager()
    await manager.connect(document_id, websocket)
    async with ws_keepalive(websocket) as keepalive:
        try:
            while True:
                raw = await websocket.receive_text()
                if is_pong(raw):
                    keepalive.notify_pong()
        except WebSocketDisconnect:
            manager.disconnect(document_id, websocket)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Document comments WS: ошибка document_id=%s: %s", document_id, exc)
            manager.disconnect(document_id, websocket)


@router.get(
    "/documents/{document_id}/comments",
    summary="Комментарии к документу",
    response_model=list[DocumentCommentRead],
)
async def list_document_comments(
    doc: AccessibleDocument,
    user: CurrentUser,
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[DocumentCommentRead]:
    rows = await comment_svc.list_comments(db, user, doc.id, skip=skip, limit=limit)
    return [_comment_to_read(r) for r in rows]


@router.post(
    "/documents/{document_id}/comments",
    summary="Добавить комментарий к документу",
    response_model=DocumentCommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_comment(
    doc: AccessibleDocument,
    user: CurrentUser,
    db: DbSession,
    body: DocumentCommentCreate,
) -> DocumentCommentRead:
    c = await comment_svc.create_comment(db, user, doc.id, body)
    return _comment_to_read(c)


@router.patch(
    "/documents/{document_id}/comments/{comment_id}",
    summary="Обновить комментарий к документу",
    response_model=DocumentCommentRead,
)
async def update_document_comment(
    doc: AccessibleDocument,
    comment_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: DocumentCommentUpdate,
) -> DocumentCommentRead:
    c = await comment_svc.update_comment(db, user, doc.id, comment_id, body)
    return _comment_to_read(c)


@router.delete(
    "/documents/{document_id}/comments/{comment_id}",
    summary="Удалить комментарий к документу",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document_comment(
    doc: AccessibleDocument,
    comment_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await comment_svc.delete_comment(db, user, doc.id, comment_id)


@router.post(
    "/documents/{document_id}/comments/rich-media",
    summary="Загрузить изображение для комментария к документу",
    response_model=RichMediaRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_comment_rich_media(
    doc: AccessibleDocument,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> RichMediaRead:
    """Загружает изображение для вставки в комментарий; сохраните id из ответа в media_ids при создании."""
    async with open_upload_stream(file, get_settings().attachment_max_size_bytes) as (file_data, file_size):
        media = await comment_svc.upload_comment_rich_media(
            db,
            user,
            doc.id,
            file_data=file_data,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            original_filename=file.filename or "image",
        )
    return rich_media_svc.rich_media_to_read(media)
