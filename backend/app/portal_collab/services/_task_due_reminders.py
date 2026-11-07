"""Периодические уведомления исполнителю: за 2 дня до срока и в день просрочки."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import now_utc
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_task_reminder_sent import PortalTaskReminderSent
from app.portal_chat.services.inbox_publish import publish_portal_notification_updates
from app.portal_collab.services._notification_access import (
    TASK_REMINDER_KIND_DUE_SOON,
    TASK_REMINDER_KIND_OVERDUE,
)
from app.portal_collab.services._notification_create import create_task_due_reminder_notifications
from app.portal_collab.services._task_assignees import load_assignee_subs_by_task_ids
from app.portal_collab.services._task_due_calendar import task_due_calendar_date, today_portal
from app.portal_collab.services.task_column import closed_task_status_keys

logger = logging.getLogger(__name__)

_CANDIDATE_HORIZON_DAYS = 3


def reminder_kind_for_due(due_at: datetime, now: datetime) -> str | None:
    """``due_soon`` на T−2, ``overdue`` с первого дня после срока, иначе None."""
    today = today_portal(now)
    due_date = task_due_calendar_date(due_at)
    if today == due_date - timedelta(days=2):
        return TASK_REMINDER_KIND_DUE_SOON
    if today >= due_date + timedelta(days=1):
        return TASK_REMINDER_KIND_OVERDUE
    return None


async def _already_sent_keys(
    session: AsyncSession,
    task_ids: list[uuid.UUID],
) -> set[tuple[uuid.UUID, str, str, datetime]]:
    if not task_ids:
        return set()
    rows = (
        await session.execute(
            select(
                PortalTaskReminderSent.task_id,
                PortalTaskReminderSent.recipient_sub,
                PortalTaskReminderSent.reminder_kind,
                PortalTaskReminderSent.due_at_snapshot,
            ).where(PortalTaskReminderSent.task_id.in_(task_ids))
        )
    ).all()
    return {(row[0], row[1], row[2], row[3]) for row in rows}


def _recipient_subs_for_task(
    task: PortalTask,
    assignees_by_id: dict[uuid.UUID, list[str]],
) -> list[str]:
    subs = list(assignees_by_id.get(task.id, []))
    if task.assignee_sub and task.assignee_sub not in subs:
        subs.append(task.assignee_sub)
    return list(dict.fromkeys(sub for sub in subs if sub))


async def process_task_due_reminders(
    session: AsyncSession,
    now: datetime | None = None,
) -> int:
    """Найти задачи в окнах срока и отправить уведомления. Возвращает число получателей."""
    moment = now or now_utc()
    closed = await closed_task_status_keys(session)
    horizon = moment + timedelta(days=_CANDIDATE_HORIZON_DAYS)
    stmt = select(PortalTask).where(
        PortalTask.due_at.is_not(None),
        PortalTask.due_at < horizon,
        PortalTask.is_tour_demo.is_(False),
    )
    if closed:
        stmt = stmt.where(PortalTask.status.not_in(closed))
    tasks = list((await session.execute(stmt)).scalars().all())
    task_ids = [task.id for task in tasks]
    assignees_by_id = await load_assignee_subs_by_task_ids(session, task_ids)
    sent_keys = await _already_sent_keys(session, task_ids)

    all_notified: dict[str, uuid.UUID] = {}
    sent_recipients = 0
    for task in tasks:
        if task.due_at is None:
            continue
        kind = reminder_kind_for_due(task.due_at, moment)
        if kind is None:
            continue
        recipients = _recipient_subs_for_task(task, assignees_by_id)
        if not recipients:
            continue
        pending = [sub for sub in recipients if (task.id, sub, kind, task.due_at) not in sent_keys]
        if not pending:
            continue
        notified = await create_task_due_reminder_notifications(
            session,
            task,
            recipient_subs=pending,
            reminder_kind=kind,
        )
        all_notified.update(notified)
        sent_recipients += len(notified)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.warning("Конфликт идемпотентности напоминаний о сроке задачи, цикл пропущен")
        return 0

    if all_notified:
        await publish_portal_notification_updates(
            list(all_notified.keys()),
            notification_ids_by_sub=all_notified,
        )
        logger.info("Отправлено напоминаний о сроке задач: %s", sent_recipients)
    return sent_recipients
