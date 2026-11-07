"""Запросы к уведомлениям (только чтение)."""

from __future__ import annotations

import logging
import uuid
from typing import Any, cast

from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


async def _get_own_notification_or_404(
    session: AsyncSession,
    user: UserPublic,
    notification_id: uuid.UUID,
) -> PortalNotification:
    """Общая проверка для get/mark-read/delete: уведомление существует и принадлежит пользователю."""
    notif = await session.get(PortalNotification, notification_id)
    if notif is None:
        raise NotFoundError("Уведомление не найдено")
    if notif.recipient_sub != user.sub:
        logger.warning(
            "Отказ в доступе к уведомлению: user_sub=%s notification_id=%s",
            user.sub,
            notification_id,
        )
        raise ForbiddenError("Нет доступа к уведомлению")
    return notif


async def list_notifications(
    session: AsyncSession,
    user: UserPublic,
    *,
    unread_only: bool = True,
    skip: int = 0,
    limit: int = 50,
) -> list[PortalNotification]:
    """Список уведомлений текущего пользователя."""
    stmt = select(PortalNotification).where(PortalNotification.recipient_sub == user.sub)
    if unread_only:
        stmt = stmt.where(PortalNotification.read_at.is_(None))
    stmt = stmt.order_by(PortalNotification.created_at.desc()).offset(skip).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def get_unread_count(
    session: AsyncSession,
    user: UserPublic,
) -> int:
    """Количество непрочитанных уведомлений пользователя."""
    stmt = (
        select(func.count())
        .select_from(PortalNotification)
        .where(
            PortalNotification.recipient_sub == user.sub,
            PortalNotification.read_at.is_(None),
        )
    )
    return (await session.execute(stmt)).scalar_one()


async def get_notification_for_user(
    session: AsyncSession,
    user: UserPublic,
    notification_id: uuid.UUID,
) -> PortalNotification:
    """Получить уведомление по id; 403, если не принадлежит пользователю."""
    return await _get_own_notification_or_404(session, user, notification_id)


async def mark_notification_read(
    session: AsyncSession,
    user: UserPublic,
    notification_id: uuid.UUID,
) -> PortalNotification:
    """Отметить уведомление прочитанным; 403, если не принадлежит текущему пользователю."""
    notif = await _get_own_notification_or_404(session, user, notification_id)
    if notif.read_at is None:
        notif.read_at = _now_utc()
        await session.commit()
    return notif


async def mark_all_notifications_read(
    session: AsyncSession,
    user: UserPublic,
) -> int:
    """Отметить все непрочитанные уведомления пользователя прочитанными. Возвращает кол-во."""
    stmt = (
        update(PortalNotification)
        .where(
            PortalNotification.recipient_sub == user.sub,
            PortalNotification.read_at.is_(None),
        )
        .values(read_at=_now_utc())
    )
    result = cast(
        CursorResult[Any],
        await session.execute(stmt),
    )
    await session.commit()
    n = result.rowcount
    return 0 if n is None or n < 0 else n


async def recipient_subs_for_task_notifications(
    session: AsyncSession,
    task_ids: list[uuid.UUID],
) -> list[str]:
    """Получатели уведомлений по задачам. Пустой список id — пустой результат."""
    if not task_ids:
        return []
    rows = await session.scalars(
        select(PortalNotification.recipient_sub).where(PortalNotification.task_id.in_(task_ids)).distinct(),
    )
    return list(rows.all())


async def delete_notification(
    session: AsyncSession,
    user: UserPublic,
    notification_id: uuid.UUID,
) -> None:
    """Удалить уведомление; 404/403 при отсутствии или чужом."""
    notif = await _get_own_notification_or_404(session, user, notification_id)
    await session.delete(notif)
    await session.commit()


async def delete_all_notifications(
    session: AsyncSession,
    user: UserPublic,
) -> int:
    """Удалить все уведомления текущего пользователя. Возвращает количество удалённых строк."""
    stmt = delete(PortalNotification).where(PortalNotification.recipient_sub == user.sub)
    result = cast(
        CursorResult[Any],
        await session.execute(stmt),
    )
    await session.commit()
    n = result.rowcount
    return 0 if n is None or n < 0 else n
