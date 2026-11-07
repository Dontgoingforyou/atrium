"""Гонки UNIQUE для напоминаний о сроке задачи."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest
from app.core.enums import TaskPriority, TaskStatus
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.infrastructure.db.models.portal_task_reminder_sent import PortalTaskReminderSent
from app.portal_collab.services._task_due_reminders import process_task_due_reminders
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.concurrency.conftest import profile_from_user
from tests.helpers.portal_test_users import user_portal_regular, user_portal_user_b

_NOW = datetime(2026, 9, 15, 12, 0, tzinfo=ZoneInfo("Europe/Moscow"))
_DUE = datetime(2026, 9, 17, tzinfo=UTC)


@pytest.mark.asyncio
async def test_parallel_process_task_due_reminders_one_sent_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Два process_task_due_reminders бьют в UNIQUE, не только в pre-check."""
    monkeypatch.setattr(
        "app.portal_collab.services._task_due_reminders._already_sent_keys",
        AsyncMock(return_value=set()),
    )
    monkeypatch.setattr(
        "app.portal_collab.services._task_due_reminders.publish_portal_notification_updates",
        AsyncMock(),
    )
    owner = user_portal_regular()
    assignee = user_portal_user_b()
    async with sqlite_concurrency_factory() as s:
        s.add_all([profile_from_user(owner), profile_from_user(assignee)])
        task = PortalTask(
            title="Гонка срока",
            creator_sub=owner.sub,
            assignee_sub=assignee.sub,
            status=TaskStatus.TODO.value,
            priority=TaskPriority.MEDIUM.value,
            due_at=_DUE,
            created_at=_NOW.astimezone(UTC),
            updated_at=_NOW.astimezone(UTC),
        )
        s.add(task)
        await s.flush()
        s.add(PortalTaskAssignee(task_id=task.id, assignee_sub=assignee.sub))
        await s.commit()

    async def try_process() -> int:
        async with sqlite_concurrency_factory() as sess:
            return await process_task_due_reminders(sess, now=_NOW)

    await asyncio.gather(try_process(), try_process())

    async with sqlite_concurrency_factory() as s:
        sent_n = await s.execute(select(func.count()).select_from(PortalTaskReminderSent))
        notif_n = await s.execute(select(func.count()).select_from(PortalNotification))
        assert sent_n.scalar_one() == 1
        assert notif_n.scalar_one() == 1
