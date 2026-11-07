"""Напоминания и publish_calendar_event."""

from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from app.core.enums import CalendarMemberRole, CalendarReminderChannel
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_calendar import (
    PortalCalendar,
    PortalCalendarAttendee,
    PortalCalendarEvent,
    PortalCalendarEventOverride,
    PortalCalendarMember,
    PortalCalendarReminder,
    PortalCalendarReminderSent,
)
from app.portal_calendar.services._realtime import publish_calendar_event
from app.portal_calendar.services._reminders import process_due_reminders
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


async def _seed_calendar_with_event(
    session: AsyncSession,
    *,
    starts_offset_minutes: int = 15,
    with_portal_attendee: bool = False,
    with_email_attendee: bool = False,
    reminder_offset: int = 15,
    cancelled: bool = False,
    title: str = "Напоминание",
    location: str | None = None,
    timezone: str = "UTC",
    rrule: str | None = None,
) -> PortalCalendarEvent:
    now = now_utc()
    cal = PortalCalendar(
        owner_sub="user-sub",
        title="Тест",
        color="#3B82F6",
        timezone="UTC",
        is_primary=True,
    )
    session.add(cal)
    await session.flush()
    session.add(
        PortalCalendarMember(
            calendar_id=cal.id,
            user_sub="user-sub",
            email="user@example.com",
            role=CalendarMemberRole.OWNER.value,
        )
    )
    starts = now + timedelta(minutes=starts_offset_minutes)
    event = PortalCalendarEvent(
        calendar_id=cal.id,
        organizer_sub="user-sub",
        title=title,
        location=location,
        starts_at=starts,
        ends_at=starts + timedelta(hours=1),
        timezone=timezone,
        rrule=rrule,
    )
    session.add(event)
    await session.flush()
    session.add(
        PortalCalendarReminder(
            event_id=event.id,
            offset_minutes=reminder_offset,
            channel=CalendarReminderChannel.PORTAL.value,
        )
    )
    if with_portal_attendee:
        session.add(
            PortalCalendarAttendee(
                event_id=event.id,
                email="b@example.com",
                user_sub="user-b",
                status="pending",
            )
        )
    if with_email_attendee:
        session.add(
            PortalCalendarAttendee(
                event_id=event.id,
                email="guest@example.com",
                user_sub=None,
                status="pending",
            )
        )
    if cancelled:
        session.add(
            PortalCalendarEventOverride(
                event_id=event.id,
                original_start=starts,
                is_cancelled=True,
            )
        )
    await session.commit()
    stmt = (
        select(PortalCalendarEvent)
        .where(PortalCalendarEvent.id == event.id)
        .options(
            selectinload(PortalCalendarEvent.reminders),
            selectinload(PortalCalendarEvent.attendees),
            selectinload(PortalCalendarEvent.overrides),
        )
    )
    return (await session.execute(stmt)).scalar_one()


@pytest.mark.asyncio
async def test_process_due_reminders_sends_and_idempotent(sqlite_session: AsyncSession) -> None:
    await _seed_calendar_with_event(
        sqlite_session,
        starts_offset_minutes=15,
        with_portal_attendee=True,
        reminder_offset=15,
    )

    with (
        patch(
            "app.portal_calendar.services._reminders.create_calendar_reminder_notifications",
            new_callable=AsyncMock,
            return_value={"user-sub": uuid.uuid4(), "user-b": uuid.uuid4()},
        ) as notify,
        patch(
            "app.portal_calendar.services._reminders.publish_portal_notification_updates",
            new_callable=AsyncMock,
        ) as inbox,
        patch(
            "app.portal_calendar.services._reminders.send_email",
            new_callable=AsyncMock,
        ) as mail,
    ):
        n1 = await process_due_reminders(sqlite_session)
        n2 = await process_due_reminders(sqlite_session)

    assert n1 == 2
    assert n2 == 0
    notify.assert_awaited()
    inbox.assert_awaited()
    mail.assert_not_awaited()

    sent = list((await sqlite_session.execute(select(PortalCalendarReminderSent))).scalars().all())
    keys = {row.recipient_key for row in sent}
    assert keys == {"sub:user-sub", "sub:user-b"}


@pytest.mark.asyncio
async def test_process_due_reminders_notifies_organizer(
    sqlite_session: AsyncSession,
) -> None:
    """Организатор всегда получает calendar_reminder (не skip-self как у invite)."""
    from app.infrastructure.db.models.portal_notification import PortalNotification

    await _seed_calendar_with_event(
        sqlite_session,
        starts_offset_minutes=15,
        with_portal_attendee=False,
        reminder_offset=15,
    )

    with (
        patch(
            "app.portal_calendar.services._reminders.publish_portal_notification_updates",
            new_callable=AsyncMock,
        ),
        patch(
            "app.portal_calendar.services._reminders.send_email",
            new_callable=AsyncMock,
        ),
    ):
        n = await process_due_reminders(sqlite_session)

    assert n == 1
    notifs = list(
        (await sqlite_session.execute(select(PortalNotification).where(PortalNotification.type == "calendar_reminder")))
        .scalars()
        .all()
    )
    assert any(n.recipient_sub == "user-sub" for n in notifs)


@pytest.mark.asyncio
async def test_process_due_reminders_organizer_also_attendee(sqlite_session: AsyncSession) -> None:
    """Организатор в attendees не должен давать UniqueViolation на reminder_sent."""
    event = await _seed_calendar_with_event(
        sqlite_session,
        starts_offset_minutes=15,
        with_portal_attendee=True,
        reminder_offset=15,
    )
    sqlite_session.add(
        PortalCalendarAttendee(
            event_id=event.id,
            email="user@example.com",
            user_sub="user-sub",
            status="accepted",
        )
    )
    await sqlite_session.commit()
    stmt = (
        select(PortalCalendarEvent)
        .where(PortalCalendarEvent.id == event.id)
        .options(
            selectinload(PortalCalendarEvent.reminders),
            selectinload(PortalCalendarEvent.attendees),
            selectinload(PortalCalendarEvent.overrides),
        )
    )
    _ = (await sqlite_session.execute(stmt)).scalar_one()

    with (
        patch(
            "app.portal_calendar.services._reminders.create_calendar_reminder_notifications",
            new_callable=AsyncMock,
            return_value={"user-sub": uuid.uuid4(), "user-b": uuid.uuid4()},
        ) as notify,
        patch(
            "app.portal_calendar.services._reminders.publish_portal_notification_updates",
            new_callable=AsyncMock,
        ) as inbox,
        patch(
            "app.portal_calendar.services._reminders.send_email",
            new_callable=AsyncMock,
        ),
    ):
        n1 = await process_due_reminders(sqlite_session)
        n2 = await process_due_reminders(sqlite_session)

    assert n1 == 2
    assert n2 == 0
    notify.assert_awaited()
    inbox.assert_awaited()
    sent = list((await sqlite_session.execute(select(PortalCalendarReminderSent))).scalars().all())
    keys = {row.recipient_key for row in sent}
    assert keys == {"sub:user-sub", "sub:user-b"}


@pytest.mark.asyncio
async def test_process_due_reminders_email_guest(sqlite_session: AsyncSession) -> None:
    await _seed_calendar_with_event(
        sqlite_session,
        starts_offset_minutes=15,
        with_email_attendee=True,
        reminder_offset=15,
    )

    with (
        patch(
            "app.portal_calendar.services._reminders.create_calendar_reminder_notifications",
            new_callable=AsyncMock,
            return_value={"user-sub": uuid.uuid4()},
        ),
        patch(
            "app.portal_calendar.services._reminders.publish_portal_notification_updates",
            new_callable=AsyncMock,
        ),
        patch(
            "app.portal_calendar.services._reminders.send_email",
            new_callable=AsyncMock,
        ) as mail,
    ):
        n = await process_due_reminders(sqlite_session)

    assert n == 2
    mail.assert_awaited()
    assert mail.await_args.kwargs["to"] == "guest@example.com"


@pytest.mark.asyncio
async def test_process_due_reminders_email_guest_not_marked_when_smtp_fails(
    sqlite_session: AsyncSession,
) -> None:
    await _seed_calendar_with_event(
        sqlite_session,
        starts_offset_minutes=15,
        with_email_attendee=True,
        reminder_offset=15,
    )

    with (
        patch(
            "app.portal_calendar.services._reminders.create_calendar_reminder_notifications",
            new_callable=AsyncMock,
            return_value={"user-sub": uuid.uuid4()},
        ),
        patch(
            "app.portal_calendar.services._reminders.publish_portal_notification_updates",
            new_callable=AsyncMock,
        ),
        patch(
            "app.portal_calendar.services._reminders.send_email",
            new_callable=AsyncMock,
            return_value=False,
        ),
    ):
        n = await process_due_reminders(sqlite_session)

    sent = list((await sqlite_session.execute(select(PortalCalendarReminderSent))).scalars().all())
    keys = {row.recipient_key for row in sent}
    assert "email:guest@example.com" not in keys
    assert keys == {"sub:user-sub"}
    assert n == 1


@pytest.mark.asyncio
async def test_process_due_reminders_includes_title_when_location(
    sqlite_session: AsyncSession,
) -> None:
    """Напоминание сохраняет снимок времени и письмо содержит title/when/location."""
    from app.infrastructure.db.models.portal_notification import PortalNotification
    from app.infrastructure.email.reminder_format import format_reminder_when

    telemost = "https://telemost.yandex.ru/j/123"
    event = await _seed_calendar_with_event(
        sqlite_session,
        starts_offset_minutes=15,
        with_email_attendee=True,
        reminder_offset=15,
        title="Стендап команды",
        location=telemost,
        timezone="Europe/Moscow",
    )
    starts = event.starts_at

    with (
        patch(
            "app.portal_calendar.services._reminders.publish_portal_notification_updates",
            new_callable=AsyncMock,
        ),
        patch(
            "app.portal_calendar.services._reminders.send_email",
            new_callable=AsyncMock,
        ) as mail,
    ):
        n = await process_due_reminders(sqlite_session)

    assert n == 2
    notifs = list((await sqlite_session.execute(select(PortalNotification))).scalars().all())
    reminder_notifs = [x for x in notifs if x.type == "calendar_reminder"]
    assert reminder_notifs
    assert reminder_notifs[0].calendar_occurrence_starts_at is not None
    got = reminder_notifs[0].calendar_occurrence_starts_at
    if got.tzinfo is None:
        got = got.replace(tzinfo=starts.tzinfo)
    assert got == starts

    mail.assert_awaited()
    text_body = mail.await_args.kwargs["text_body"]
    assert "Стендап команды" in text_body
    assert telemost in text_body
    when = format_reminder_when(starts, timezone="Europe/Moscow")
    assert when in text_body
    assert "МСК" in when


@pytest.mark.asyncio
async def test_process_due_reminders_after_reschedule_still_sends(
    sqlite_session: AsyncSession,
) -> None:
    """fire_at в прошлом, событие ещё не закончилось — напоминание уходит."""
    await _seed_calendar_with_event(
        sqlite_session,
        starts_offset_minutes=10,
        with_portal_attendee=True,
        reminder_offset=30,
    )

    with (
        patch(
            "app.portal_calendar.services._reminders.create_calendar_reminder_notifications",
            new_callable=AsyncMock,
            return_value={"user-sub": uuid.uuid4(), "user-b": uuid.uuid4()},
        ) as notify,
        patch(
            "app.portal_calendar.services._reminders.publish_portal_notification_updates",
            new_callable=AsyncMock,
        ),
        patch(
            "app.portal_calendar.services._reminders.send_email",
            new_callable=AsyncMock,
        ),
    ):
        n = await process_due_reminders(sqlite_session)

    assert n == 2
    notify.assert_awaited()


@pytest.mark.asyncio
async def test_process_due_reminders_skips_ended_past_grace(
    sqlite_session: AsyncSession,
) -> None:
    """Событие закончилось больше чем 5 минут назад — skip."""
    await _seed_calendar_with_event(
        sqlite_session,
        starts_offset_minutes=-70,
        reminder_offset=15,
    )

    with (
        patch(
            "app.portal_calendar.services._reminders.create_calendar_reminder_notifications",
            new_callable=AsyncMock,
            return_value={},
        ) as notify,
        patch(
            "app.portal_calendar.services._reminders.publish_portal_notification_updates",
            new_callable=AsyncMock,
        ),
    ):
        n = await process_due_reminders(sqlite_session)

    assert n == 0
    notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_due_reminders_skips_invalid_rrule(
    sqlite_session: AsyncSession,
) -> None:
    await _seed_calendar_with_event(
        sqlite_session,
        starts_offset_minutes=15,
        reminder_offset=15,
        rrule="NOT-A-RULE",
    )

    with (
        patch(
            "app.portal_calendar.services._reminders.create_calendar_reminder_notifications",
            new_callable=AsyncMock,
            return_value={},
        ) as notify,
        patch(
            "app.portal_calendar.services._reminders.publish_portal_notification_updates",
            new_callable=AsyncMock,
        ),
    ):
        n = await process_due_reminders(sqlite_session)

    assert n == 0
    notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_due_reminders_recurring_occurrence_in_window(
    sqlite_session: AsyncSession,
) -> None:
    """RRULE: вчерашний occ отсекается grace, сегодняшний due — уходит."""
    await _seed_calendar_with_event(
        sqlite_session,
        starts_offset_minutes=15 - 24 * 60,
        reminder_offset=15,
        rrule="FREQ=DAILY;COUNT=5",
    )

    with (
        patch(
            "app.portal_calendar.services._reminders.create_calendar_reminder_notifications",
            new_callable=AsyncMock,
            return_value={"user-sub": uuid.uuid4()},
        ) as notify,
        patch(
            "app.portal_calendar.services._reminders.publish_portal_notification_updates",
            new_callable=AsyncMock,
        ),
        patch(
            "app.portal_calendar.services._reminders.send_email",
            new_callable=AsyncMock,
        ),
    ):
        n = await process_due_reminders(sqlite_session)

    assert n == 1
    notify.assert_awaited()


@pytest.mark.asyncio
async def test_process_due_reminders_skips_cancelled(sqlite_session: AsyncSession) -> None:
    await _seed_calendar_with_event(
        sqlite_session,
        starts_offset_minutes=15,
        reminder_offset=15,
        cancelled=True,
    )

    with (
        patch(
            "app.portal_calendar.services._reminders.create_calendar_reminder_notifications",
            new_callable=AsyncMock,
            return_value={},
        ) as notify,
        patch(
            "app.portal_calendar.services._reminders.publish_portal_notification_updates",
            new_callable=AsyncMock,
        ),
    ):
        n = await process_due_reminders(sqlite_session)

    assert n == 0
    notify.assert_not_awaited()


@pytest.mark.asyncio
async def test_publish_calendar_event_swallows_error(caplog: pytest.LogCaptureFixture) -> None:
    manager = AsyncMock()
    manager.publish.side_effect = RuntimeError("redis down")
    with (
        patch(
            "app.portal_calendar.services._realtime.get_calendar_manager",
            return_value=manager,
        ),
        caplog.at_level("ERROR"),
    ):
        await publish_calendar_event("calendar_updated", actor_sub="user-sub")
    assert any("Не удалось опубликовать событие календаря" in rec.message for rec in caplog.records)
