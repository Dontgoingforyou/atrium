"""Гонка отправки напоминания календаря."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest
from app.core.enums import CalendarMemberRole, CalendarReminderChannel
from app.infrastructure.db.models.portal_calendar import (
    PortalCalendar,
    PortalCalendarEvent,
    PortalCalendarMember,
    PortalCalendarReminder,
    PortalCalendarReminderSent,
)
from app.portal_calendar.services._reminders import process_due_reminders
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.concurrency.conftest import profile_from_user
from tests.helpers.portal_test_users import user_portal_regular


@pytest.mark.asyncio
async def test_parallel_process_due_reminders_one_sent_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Два process_due_reminders бьют в UNIQUE, не только в _already_sent."""
    monkeypatch.setattr(
        "app.portal_calendar.services._reminders._already_sent",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.portal_calendar.services._reminders.create_calendar_reminder_notifications",
        AsyncMock(return_value={}),
    )
    monkeypatch.setattr(
        "app.portal_calendar.services._reminders.publish_portal_notification_updates",
        AsyncMock(),
    )
    monkeypatch.setattr(
        "app.portal_calendar.services._reminders.send_email",
        AsyncMock(return_value=True),
    )
    owner = user_portal_regular()
    cal_id = uuid.uuid4()
    event_id = uuid.uuid4()
    now = datetime.now(UTC)
    starts = now + timedelta(minutes=15)
    async with sqlite_concurrency_factory() as s:
        s.add(profile_from_user(owner))
        s.add(PortalCalendar(id=cal_id, owner_sub=owner.sub, title="Кал", is_primary=True))
        s.add(
            PortalCalendarMember(
                calendar_id=cal_id,
                user_sub=owner.sub,
                email=owner.email,
                role=CalendarMemberRole.OWNER.value,
            )
        )
        s.add(
            PortalCalendarEvent(
                id=event_id,
                calendar_id=cal_id,
                organizer_sub=owner.sub,
                title="Встреча",
                starts_at=starts,
                ends_at=starts + timedelta(hours=1),
            )
        )
        s.add(
            PortalCalendarReminder(
                event_id=event_id,
                offset_minutes=15,
                channel=CalendarReminderChannel.PORTAL.value,
            )
        )
        await s.commit()

    async def try_process() -> int:
        async with sqlite_concurrency_factory() as sess:
            return await process_due_reminders(sess)

    await asyncio.gather(try_process(), try_process())

    async with sqlite_concurrency_factory() as s:
        n = await s.execute(select(func.count()).select_from(PortalCalendarReminderSent))
        assert n.scalar_one() == 1
