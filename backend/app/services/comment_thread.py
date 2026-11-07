from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any, Protocol

from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.exc import NoInspectionAvailable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
from app.infrastructure.ws.room_manager import TopicRoomManager
from app.portal_chat.comment_thread_events import COMMENT_THREAD_UPDATED_EVENT
from app.schemas.auth import UserPublic


class CommentThreadOrm(Protocol):
    """ORM-модель top-level комментария с replies (task/document/section)."""

    id: Any
    parent_id: Any
    created_at: Any
    replies: Any


async def get_comment_for_host_or_404[TComment](
    session: AsyncSession,
    model: type[TComment],
    comment_id: uuid.UUID,
    host_id: uuid.UUID,
    host_fk_attr: str,
) -> TComment:
    comment = await session.get(model, comment_id)
    if comment is None or getattr(comment, host_fk_attr) != host_id:
        raise NotFoundError("Комментарий не найден")
    return comment


def _assign_replies(comment: Any, children: list[Any]) -> None:
    try:
        sa_inspect(comment)
    except NoInspectionAvailable:
        comment.replies = children
        return
    # Не помечать коллекцию изменённой: это чтение, не правка parent_id.
    set_committed_value(comment, "replies", children)


def attach_comment_replies[TComment: CommentThreadOrm](comments: Sequence[TComment]) -> list[TComment]:
    """Собирает дерево по parent_id. Цикл не обходится повторно."""
    children_by_parent: dict[Any, list[TComment]] = {}
    roots: list[TComment] = []
    for comment in comments:
        parent_id = comment.parent_id
        if parent_id is None:
            roots.append(comment)
        else:
            children_by_parent.setdefault(parent_id, []).append(comment)

    def attach(comment: TComment, ancestors: set[Any]) -> None:
        own_id = comment.id
        if own_id in ancestors:
            _assign_replies(comment, [])
            return
        ancestors.add(own_id)
        nested: list[TComment] = []
        for child in children_by_parent.get(own_id, []):
            if child.id in ancestors:
                continue
            attach(child, ancestors)
            nested.append(child)
        ancestors.remove(own_id)
        _assign_replies(comment, nested)

    for root in roots:
        attach(root, set())
    return roots


async def list_top_level_comments[TComment: CommentThreadOrm](
    session: AsyncSession,
    model: type[TComment],
    host_fk_attr: str,
    host_id: uuid.UUID | str,
    *,
    skip: int = 0,
    limit: int = 200,
    extra_options: Sequence[Any] | None = None,
) -> list[TComment]:
    """Корни хоста с ответами. skip и limit режут только корни."""
    host_col = getattr(model, host_fk_attr)
    stmt = select(model).where(host_col == host_id).order_by(model.created_at)
    if extra_options:
        stmt = stmt.options(*extra_options)
    rows = list((await session.execute(stmt)).scalars().unique().all())
    return attach_comment_replies(rows)[skip : skip + limit]


async def validate_parent_comment[TComment](
    session: AsyncSession,
    model: type[TComment],
    parent_id: uuid.UUID,
    host_id: uuid.UUID | str,
    host_fk_attr: str,
) -> None:
    parent = await session.get(model, parent_id)
    if parent is None or getattr(parent, host_fk_attr) != host_id:
        raise NotFoundError("Родительский комментарий не найден")


async def validate_comment_media_ids(
    session: AsyncSession,
    user: UserPublic,
    media_ids: Sequence[uuid.UUID],
    *,
    host_fk_attr: str,
    host_id: uuid.UUID | str,
) -> None:
    """Проверяет, что вложения (``PortalRichMedia``) принадлежат ``host_id`` и загружены текущим пользователем.

    Общая проверка для комментариев задачи, документа и специалиста.
    """
    if not media_ids:
        return
    result = await session.execute(select(PortalRichMedia).where(PortalRichMedia.id.in_(media_ids)))
    rows = {m.id: m for m in result.scalars().all()}
    for media_id in media_ids:
        media = rows.get(media_id)
        if media is None:
            raise NotFoundError("Изображение не найдено")
        if getattr(media, host_fk_attr) != host_id:
            raise ForbiddenError("Изображение не принадлежит этому ресурсу")
        if media.uploader_sub != user.sub:
            raise ForbiddenError("Нет прав на использование этого изображения")


def assert_author_or_admin(
    user: UserPublic,
    comment: Any,
    *,
    detail: str = "Нет прав на изменение комментария",
) -> None:
    if not user.is_portal_admin and comment.author_sub != user.sub:
        raise ForbiddenError(detail)


def apply_comment_fields(
    comment: Any,
    *,
    body: str | None,
    mentions: list[str] | None,
    updated_at: Any,
) -> None:
    if body is not None:
        comment.body = body
    if mentions is not None:
        comment.mentions = mentions
    comment.updated_at = updated_at


async def publish_thread_updated(manager: TopicRoomManager, room_id: uuid.UUID) -> None:
    await manager.publish(room_id, {"event": COMMENT_THREAD_UPDATED_EVENT})
