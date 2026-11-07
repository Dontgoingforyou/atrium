from __future__ import annotations

import uuid
from typing import Any, BinaryIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.optimistic_lock import compare_and_swap_row
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
from app.infrastructure.db.models.portal_task import PortalTaskComment, PortalTaskCommentMedia
from app.infrastructure.ws.managers import get_task_comments_manager
from app.portal_chat.services.inbox_publish import publish_portal_notification_updates
from app.portal_collab.schemas.task import TaskCommentCreate, TaskCommentUpdate
from app.portal_collab.services import notification as notification_svc
from app.portal_collab.services.task import get_task
from app.portal_collab.services.task_jira_schedule import schedule_comment_jira_push
from app.schemas.auth import UserPublic
from app.services import comment_thread as thread_svc
from app.services import rich_media as rich_media_svc

_HOST_FK = "task_id"


async def upload_comment_rich_media(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    *,
    file_data: BinaryIO,
    file_size: int,
    content_type: str,
    original_filename: str,
) -> PortalRichMedia:
    """Загружает изображение для комментария к задаче и фиксирует транзакцию."""
    media = await rich_media_svc.upload_task_rich_media(
        session,
        user,
        task_id,
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
) -> PortalTaskComment:
    """Перезагружает комментарий с replies и вложениями (comment_media → rich_media)."""
    stmt = (
        select(PortalTaskComment)
        .where(PortalTaskComment.id == comment_id)
        .options(
            selectinload(PortalTaskComment.replies).selectinload(PortalTaskComment.comment_media),
            selectinload(PortalTaskComment.comment_media),
        )
    )
    return (await session.execute(stmt)).scalar_one()


async def list_comments(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 200,
) -> list[PortalTaskComment]:
    """Список корневых комментариев задачи."""
    await get_task(session, user, task_id)
    return await thread_svc.list_top_level_comments(
        session,
        PortalTaskComment,
        _HOST_FK,
        task_id,
        skip=skip,
        limit=limit,
        extra_options=[
            selectinload(PortalTaskComment.comment_media),
        ],
    )


async def create_comment(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    data: TaskCommentCreate,
) -> PortalTaskComment:
    task = await get_task(session, user, task_id)
    if data.parent_id is not None:
        await thread_svc.validate_parent_comment(
            session,
            PortalTaskComment,
            data.parent_id,
            task_id,
            _HOST_FK,
        )
    await thread_svc.validate_comment_media_ids(
        session,
        user,
        data.media_ids or [],
        host_fk_attr=_HOST_FK,
        host_id=task_id,
    )
    now = _now_utc()
    comment = PortalTaskComment(
        task_id=task_id,
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
        session.add(PortalTaskCommentMedia(comment_id=comment.id, media_id=media_id))
    notified = await notification_svc.create_mention_notifications(session, task, comment, user.sub)
    comment_notified = await notification_svc.create_comment_notifications(
        session,
        task,
        comment,
        user.sub,
        already_notified=set(notified),
    )
    notified.update(comment_notified)
    await session.commit()

    await publish_portal_notification_updates(list(notified.keys()), notification_ids_by_sub=notified)
    await thread_svc.publish_thread_updated(get_task_comments_manager(), task_id)
    schedule_comment_jira_push(comment.id)
    return await _reload_comment_with_media(session, comment.id)


async def update_comment(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    data: TaskCommentUpdate,
) -> PortalTaskComment:
    await get_task(session, user, task_id)
    comment = await thread_svc.get_comment_for_host_or_404(
        session,
        PortalTaskComment,
        comment_id,
        task_id,
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
        PortalTaskComment,
        entity_id=comment_id,
        expected_version=data.expected_version,
        values=values,
        conflict_message="Комментарий изменён другим пользователем",
    )
    await session.refresh(comment)
    comment.version = new_version
    await session.commit()
    await thread_svc.publish_thread_updated(get_task_comments_manager(), task_id)
    return await _reload_comment_with_media(session, comment_id)


async def delete_comment(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
) -> None:
    await get_task(session, user, task_id)
    comment = await thread_svc.get_comment_for_host_or_404(
        session,
        PortalTaskComment,
        comment_id,
        task_id,
        _HOST_FK,
    )
    thread_svc.assert_author_or_admin(user, comment, detail="Нет прав на удаление комментария")
    await session.delete(comment)
    await session.commit()
    await thread_svc.publish_thread_updated(get_task_comments_manager(), task_id)
