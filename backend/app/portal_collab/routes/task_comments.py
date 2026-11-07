from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, File, Query, UploadFile, WebSocket, WebSocketDisconnect, status

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_task import PortalTaskComment
from app.infrastructure.ws import tickets as ws_ticket_svc
from app.infrastructure.ws.keepalive import is_pong, ws_keepalive
from app.infrastructure.ws.managers import get_task_comments_manager
from app.portal_chat.schemas.chat import PortalChatWsTicketRead
from app.portal_collab.schemas.task import (
    TaskCommentCreate,
    TaskCommentRead,
    TaskCommentUpdate,
)
from app.portal_collab.services import task as svc
from app.portal_collab.services import task_comment as comment_svc
from app.schemas.rich_media import RichMediaRead
from app.services import rich_media as rich_media_svc
from app.services.file_upload_validation import open_upload_stream

router = APIRouter(prefix="/portal", tags=["Задачи"])
ws_router = APIRouter(prefix="/portal", tags=["Задачи"])
logger = logging.getLogger(__name__)


def _comment_to_read(comment: PortalTaskComment) -> TaskCommentRead:
    """Строит TaskCommentRead с presigned URL для вложений (рекурсивно для replies)."""
    return TaskCommentRead(
        id=comment.id,
        task_id=comment.task_id,
        parent_id=comment.parent_id,
        author_sub=comment.author_sub,
        body=comment.body,
        mentions=list(comment.mentions or []),
        version=getattr(comment, "version", 1) or 1,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        replies=[_comment_to_read(r) for r in (comment.replies or [])],
        media=[rich_media_svc.rich_media_to_read(rm) for rm in comment.media],
    )


@router.get(
    "/tasks/{task_id}/comments",
    summary="Список комментариев задачи",
    response_model=list[TaskCommentRead],
)
async def list_task_comments(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[TaskCommentRead]:
    rows = await comment_svc.list_comments(db, user, task_id, skip=skip, limit=limit)
    return [_comment_to_read(r) for r in rows]


@router.post(
    "/tasks/{task_id}/comments",
    summary="Добавить комментарий к задаче",
    response_model=TaskCommentRead,
    status_code=201,
)
async def create_task_comment(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: TaskCommentCreate,
) -> TaskCommentRead:
    comment = await comment_svc.create_comment(db, user, task_id, body)
    return _comment_to_read(comment)


@router.patch(
    "/tasks/{task_id}/comments/{comment_id}",
    summary="Обновить комментарий",
    response_model=TaskCommentRead,
)
async def update_task_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: TaskCommentUpdate,
) -> TaskCommentRead:
    comment = await comment_svc.update_comment(db, user, task_id, comment_id, body)
    return _comment_to_read(comment)


@router.delete(
    "/tasks/{task_id}/comments/{comment_id}",
    summary="Удалить комментарий",
    status_code=204,
)
async def delete_task_comment(
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await comment_svc.delete_comment(db, user, task_id, comment_id)


@router.post(
    "/tasks/{task_id}/comments/rich-media",
    summary="Загрузить изображение для комментария к задаче",
    response_model=RichMediaRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_task_comment_rich_media(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
) -> RichMediaRead:
    """Загружает изображение для вставки в комментарий; сохраните id из ответа в media_ids при создании комментария."""
    async with open_upload_stream(file, get_settings().attachment_max_size_bytes) as (file_data, file_size):
        media = await comment_svc.upload_comment_rich_media(
            db,
            user,
            task_id,
            file_data=file_data,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            original_filename=file.filename or "image",
        )
    return rich_media_svc.rich_media_to_read(media)


@router.post(
    "/tasks/{task_id}/comments/ws-ticket",
    summary="Тикет WebSocket треда комментариев к задаче",
    response_model=PortalChatWsTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_comments_ws_ticket(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalChatWsTicketRead:
    await svc.get_task(db, user, task_id)
    t = await ws_ticket_svc.issue_task_comments_ws_ticket(task_id, user)
    return PortalChatWsTicketRead(ticket=t)


@ws_router.websocket("/tasks/{task_id}/comments/ws")
async def task_comments_websocket(
    websocket: WebSocket,
    task_id: uuid.UUID,
    db: DbSession,
    ticket: str = Query(..., min_length=8, description="Одноразовый тикет из POST .../comments/ws-ticket"),
) -> None:
    """WebSocket: обновления треда комментариев задачи."""
    parsed = await ws_ticket_svc.consume_task_comments_ws_ticket(ticket)
    if parsed is None:
        await websocket.close(code=4001)
        return
    t_id, user = parsed
    if t_id != task_id:
        await websocket.close(code=4001)
        return
    try:
        await svc.get_task(db, user, task_id)
    except (NotFoundError, ForbiddenError):
        logger.warning(
            "Отказ в доступе: Task comments WS user_sub=%s resource=task/%s",
            user.sub,
            task_id,
        )
        await websocket.close(code=4001)
        return

    manager = get_task_comments_manager()
    await manager.connect(task_id, websocket)
    async with ws_keepalive(websocket) as keepalive:
        try:
            while True:
                raw = await websocket.receive_text()
                if is_pong(raw):
                    keepalive.notify_pong()
        except WebSocketDisconnect:
            manager.disconnect(task_id, websocket)
        except Exception as exc:
            logger.exception("Task comments WS: ошибка (task_id=%s): %s", task_id, exc)
            manager.disconnect(task_id, websocket)
