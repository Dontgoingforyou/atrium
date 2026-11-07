"""Уведомления по задаче: @mention и новый комментарий без mention."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskComment
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.services._notification_access import (
    NOTIFICATION_TYPE_COMMENT,
    NOTIFICATION_TYPE_MENTION,
    batch_task_access_check,
)
from app.portal_collab.services._notification_rows import add_comment_notification_row, notification_row_id

logger = logging.getLogger(__name__)


async def _task_comment_participant_subs(session: AsyncSession, task: PortalTask) -> set[str]:
    participants: set[str] = set()
    if task.creator_sub:
        participants.add(task.creator_sub)
    if task.assignee_sub:
        participants.add(task.assignee_sub)
    if task.id is not None:
        junction = await session.execute(
            select(PortalTaskAssignee.assignee_sub).where(PortalTaskAssignee.task_id == task.id)
        )
        participants.update(row[0] for row in junction.all() if row[0])
    return participants


async def create_mention_notifications(
    session: AsyncSession,
    task: PortalTask,
    comment: PortalTaskComment,
    author_sub: str,
) -> dict[str, uuid.UUID]:
    mentioned = set(comment.mentions or []) - {author_sub}
    if not mentioned:
        return {}

    profiles_result = await session.execute(select(PortalUserProfile).where(PortalUserProfile.sub.in_(list(mentioned))))
    profiles_by_sub: dict[str, PortalUserProfile] = {p.sub: p for p in profiles_result.scalars().all()}
    can_access = await batch_task_access_check(session, mentioned, task, profiles_by_sub)

    notified: dict[str, uuid.UUID] = {}
    for recipient_sub in mentioned:
        if recipient_sub not in can_access:
            logger.debug(
                "Пропуск уведомления: получатель %s не имеет доступа к задаче %s",
                recipient_sub,
                task.id,
            )
            continue
        nid = notification_row_id()
        saved = await add_comment_notification_row(
            session,
            PortalNotification(
                id=nid,
                recipient_sub=recipient_sub,
                type=NOTIFICATION_TYPE_MENTION,
                task_id=task.id,
                comment_id=comment.id,
                author_sub=author_sub,
                created_at=_now_utc(),
            ),
            recipient_sub=recipient_sub,
            comment_id=comment.id,
        )
        if saved is not None:
            notified[recipient_sub] = saved
    return notified


async def create_comment_notifications(
    session: AsyncSession,
    task: PortalTask,
    comment: PortalTaskComment,
    author_sub: str,
    *,
    already_notified: set[str] | None = None,
) -> dict[str, uuid.UUID]:
    """Уведомление участникам задачи о новом комментарии (не автору, не тем, кто уже получил mention)."""
    skip = set(already_notified or ())
    skip.add(author_sub)
    candidates = await _task_comment_participant_subs(session, task)
    candidates -= skip
    if not candidates:
        return {}

    profiles_result = await session.execute(
        select(PortalUserProfile).where(PortalUserProfile.sub.in_(list(candidates)))
    )
    profiles_by_sub: dict[str, PortalUserProfile] = {p.sub: p for p in profiles_result.scalars().all()}
    can_access = await batch_task_access_check(session, candidates, task, profiles_by_sub)

    notified: dict[str, uuid.UUID] = {}
    for recipient_sub in candidates:
        if recipient_sub not in can_access:
            logger.debug(
                "Пропуск уведомления о комментарии: получатель %s не имеет доступа к задаче %s",
                recipient_sub,
                task.id,
            )
            continue
        nid = notification_row_id()
        saved = await add_comment_notification_row(
            session,
            PortalNotification(
                id=nid,
                recipient_sub=recipient_sub,
                type=NOTIFICATION_TYPE_COMMENT,
                task_id=task.id,
                comment_id=comment.id,
                author_sub=author_sub,
                created_at=_now_utc(),
            ),
            recipient_sub=recipient_sub,
            comment_id=comment.id,
        )
        if saved is not None:
            notified[recipient_sub] = saved
    return notified
