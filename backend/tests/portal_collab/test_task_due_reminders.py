"""Окна и дедуп уведомлений о сроке задачи."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.infrastructure.db.models.portal_task_reminder_sent import PortalTaskReminderSent
from app.portal_collab.services._notification_access import (
    NOTIFICATION_TYPE_TASK_DUE_SOON,
    NOTIFICATION_TYPE_TASK_OVERDUE,
    TASK_REMINDER_KIND_DUE_SOON,
)
from app.portal_collab.services._task_due_reminders import process_task_due_reminders
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

_MSK = ZoneInfo("Europe/Moscow")
_NOW = datetime(2026, 9, 15, 12, 0, tzinfo=_MSK)


def _due_utc(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=UTC)


def _task(
    *,
    title: str,
    due_at: datetime | None,
    assignee_sub: str | None = "user-b",
    status: str = TaskStatus.TODO.value,
    is_tour_demo: bool = False,
    creator_sub: str = "user-sub",
) -> PortalTask:
    return PortalTask(
        title=title,
        creator_sub=creator_sub,
        assignee_sub=assignee_sub,
        status=status,
        priority=TaskPriority.MEDIUM.value,
        due_at=due_at,
        is_tour_demo=is_tour_demo,
        created_at=_NOW.astimezone(UTC),
        updated_at=_NOW.astimezone(UTC),
    )


async def _add_task(session: AsyncSession, task: PortalTask) -> PortalTask:
    session.add(task)
    await session.flush()
    if task.assignee_sub:
        session.add(PortalTaskAssignee(task_id=task.id, assignee_sub=task.assignee_sub))
        await session.flush()
    return task


@pytest.fixture
def _publish(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    pub = AsyncMock()
    monkeypatch.setattr(
        "app.portal_collab.services._task_due_reminders.publish_portal_notification_updates",
        pub,
    )
    return pub


@pytest.mark.asyncio
async def test_due_soon_notifies_assignee(sqlite_session: AsyncSession, _publish: AsyncMock) -> None:
    task = await _add_task(sqlite_session, _task(title="Скоро срок", due_at=_due_utc(2026, 9, 17)))
    n = await process_task_due_reminders(sqlite_session, now=_NOW)
    assert n == 1
    row = (await sqlite_session.execute(select(PortalNotification))).scalars().one()
    assert row.type == NOTIFICATION_TYPE_TASK_DUE_SOON
    assert row.recipient_sub == "user-b"
    assert row.task_id == task.id
    sent = (await sqlite_session.execute(select(PortalTaskReminderSent))).scalars().one()
    assert sent.reminder_kind == TASK_REMINDER_KIND_DUE_SOON
    _publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_overdue_first_day_notifies(sqlite_session: AsyncSession, _publish: AsyncMock) -> None:
    await _add_task(sqlite_session, _task(title="Просрочена", due_at=_due_utc(2026, 9, 14)))
    n = await process_task_due_reminders(sqlite_session, now=_NOW)
    assert n == 1
    row = (await sqlite_session.execute(select(PortalNotification))).scalars().one()
    assert row.type == NOTIFICATION_TYPE_TASK_OVERDUE


@pytest.mark.asyncio
async def test_due_day_itself_does_not_notify(sqlite_session: AsyncSession, _publish: AsyncMock) -> None:
    await _add_task(sqlite_session, _task(title="Сегодня срок", due_at=_due_utc(2026, 9, 15)))
    n = await process_task_due_reminders(sqlite_session, now=_NOW)
    assert n == 0
    assert (await sqlite_session.execute(select(func.count()).select_from(PortalNotification))).scalar_one() == 0
    _publish.assert_not_awaited()


@pytest.mark.asyncio
async def test_overdue_catchup_after_missed_day(sqlite_session: AsyncSession, _publish: AsyncMock) -> None:
    await _add_task(sqlite_session, _task(title="Давно просрочена", due_at=_due_utc(2026, 9, 10)))
    n = await process_task_due_reminders(sqlite_session, now=_NOW)
    assert n == 1
    row = (await sqlite_session.execute(select(PortalNotification))).scalars().one()
    assert row.type == NOTIFICATION_TYPE_TASK_OVERDUE


@pytest.mark.asyncio
async def test_skips_no_due_done_tour_and_no_assignee(
    sqlite_session: AsyncSession,
    _publish: AsyncMock,
) -> None:
    await _add_task(sqlite_session, _task(title="Без срока", due_at=None))
    await _add_task(
        sqlite_session,
        _task(title="Готово", due_at=_due_utc(2026, 9, 14), status=TaskStatus.DONE.value),
    )
    await _add_task(
        sqlite_session,
        _task(title="Тур", due_at=_due_utc(2026, 9, 17), is_tour_demo=True),
    )
    await _add_task(sqlite_session, _task(title="Никто", due_at=_due_utc(2026, 9, 17), assignee_sub=None))
    n = await process_task_due_reminders(sqlite_session, now=_NOW)
    assert n == 0
    assert (await sqlite_session.execute(select(func.count()).select_from(PortalNotification))).scalar_one() == 0


@pytest.mark.asyncio
async def test_idempotent_same_due_at(sqlite_session: AsyncSession, _publish: AsyncMock) -> None:
    await _add_task(sqlite_session, _task(title="Один раз", due_at=_due_utc(2026, 9, 17)))
    first = await process_task_due_reminders(sqlite_session, now=_NOW)
    second = await process_task_due_reminders(sqlite_session, now=_NOW)
    assert first == 1
    assert second == 0
    assert (await sqlite_session.execute(select(func.count()).select_from(PortalNotification))).scalar_one() == 1
    assert (await sqlite_session.execute(select(func.count()).select_from(PortalTaskReminderSent))).scalar_one() == 1


@pytest.mark.asyncio
async def test_new_due_at_sends_again(sqlite_session: AsyncSession, _publish: AsyncMock) -> None:
    task = await _add_task(sqlite_session, _task(title="Сдвиг срока", due_at=_due_utc(2026, 9, 17)))
    await process_task_due_reminders(sqlite_session, now=_NOW)
    task.due_at = _due_utc(2026, 9, 18)
    await sqlite_session.commit()
    later = _NOW + timedelta(days=1)
    n = await process_task_due_reminders(sqlite_session, now=later)
    assert n == 1
    types = list(
        (await sqlite_session.execute(select(PortalNotification.type).order_by(PortalNotification.created_at)))
        .scalars()
        .all()
    )
    assert types == [NOTIFICATION_TYPE_TASK_DUE_SOON, NOTIFICATION_TYPE_TASK_DUE_SOON]
    assert (await sqlite_session.execute(select(func.count()).select_from(PortalTaskReminderSent))).scalar_one() == 2


@pytest.mark.asyncio
async def test_notifies_all_assignees(sqlite_session: AsyncSession, _publish: AsyncMock) -> None:
    task = await _add_task(sqlite_session, _task(title="Двое", due_at=_due_utc(2026, 9, 17), assignee_sub="user-b"))
    sqlite_session.add(PortalTaskAssignee(task_id=task.id, assignee_sub="user-sub"))
    await sqlite_session.flush()
    n = await process_task_due_reminders(sqlite_session, now=_NOW)
    assert n == 2
    recipients = set((await sqlite_session.execute(select(PortalNotification.recipient_sub))).scalars().all())
    assert recipients == {"user-b", "user-sub"}
