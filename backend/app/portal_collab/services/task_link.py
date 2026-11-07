from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_task import PortalTaskLink
from app.portal_collab.schemas.task import TaskLinkCreate
from app.portal_collab.services.task import get_task
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


async def list_links(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
) -> list[PortalTaskLink]:
    """Список ссылок задачи. Доступ — как у просмотра самой задачи."""
    await get_task(session, user, task_id)
    result = await session.execute(
        select(PortalTaskLink).where(PortalTaskLink.task_id == task_id).order_by(PortalTaskLink.created_at)
    )
    return list(result.scalars().all())


async def create_link(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    body: TaskLinkCreate,
) -> PortalTaskLink:
    """Прикрепить ссылку к задаче. Право — как у просмотра задачи."""
    await get_task(session, user, task_id)
    link = PortalTaskLink(
        task_id=task_id,
        title=body.title,
        url=body.url,
        created_by_sub=user.sub,
    )
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


async def delete_link(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    link_id: uuid.UUID,
) -> None:
    """Удалить ссылку. Право — только автор ссылки или portal_admin."""
    await get_task(session, user, task_id)
    result = await session.execute(
        select(PortalTaskLink).where(
            PortalTaskLink.id == link_id,
            PortalTaskLink.task_id == task_id,
        )
    )
    link = result.scalar_one_or_none()
    if link is None:
        raise NotFoundError("Ссылка не найдена")
    if link.created_by_sub != user.sub and not user.is_portal_admin:
        logger.warning(
            "Отказ в доступе: удаление чужой ссылки задачи user_sub=%s task_id=%s link_id=%s",
            user.sub,
            task_id,
            link_id,
        )
        raise ForbiddenError("Удалять ссылку может только её автор или администратор")
    await session.delete(link)
    await session.commit()
