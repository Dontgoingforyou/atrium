"""Отправка напоминаний о событиях."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.utils import now_utc
from app.infrastructure.db.models.portal_calendar import (
    PortalCalendarEvent,
    PortalCalendarReminder,
    PortalCalendarReminderSent,
)
from app.infrastructure.email.smtp import send_email
from app.infrastructure.email.templates import reminder_email
from app.portal_calendar.services._recurrence import Occurrence, expand_event_occurrences
from app.portal_chat.services.inbox_publish import publish_portal_notification_updates
from app.portal_collab.services.notification import create_calendar_reminder_notifications

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _PendingEmail:
    to: str
    subject: str
    text_body: str
    html_body: str
    reminder_id: object
    occurrence_start: datetime
    recipient_key: str


async def process_due_reminders(session: AsyncSession) -> int:
    """Найти и отправить due-напоминания. Возвращает число успешных отправок."""
    now = now_utc()
    window_end = now + timedelta(days=8)
    window_start = now - timedelta(hours=1)

    effective_end = func.coalesce(PortalCalendarEvent.ends_at, PortalCalendarEvent.starts_at)
    has_reminder = exists().where(PortalCalendarReminder.event_id == PortalCalendarEvent.id)
    stmt = (
        select(PortalCalendarEvent)
        .options(
            selectinload(PortalCalendarEvent.reminders),
            selectinload(PortalCalendarEvent.attendees),
            selectinload(PortalCalendarEvent.overrides),
        )
        .where(has_reminder)
        .where(
            (PortalCalendarEvent.rrule.is_not(None))
            | ((PortalCalendarEvent.starts_at < window_end) & (effective_end > window_start))
        )
    )
    events = list((await session.execute(stmt)).scalars().all())
    sent_count = 0
    all_notified: dict[str, uuid.UUID] = {}
    pending_emails: list[_PendingEmail] = []

    for event in events:
        reminders = list(event.reminders or [])
        if not reminders:
            continue
        try:
            occurrences = expand_event_occurrences(event, window_start, window_end)
        except Exception:
            logger.warning(
                "Пропуск события с невалидным RRULE: event_id=%s",
                event.id,
                exc_info=True,
            )
            continue
        for occ in occurrences:
            if occ.is_cancelled:
                continue
            for reminder in reminders:
                fire_at = occ.starts_at - timedelta(minutes=reminder.offset_minutes)
                if fire_at > now:
                    continue
                event_end = occ.ends_at if occ.ends_at is not None else occ.starts_at
                if event_end < now - timedelta(minutes=5):
                    continue
                n_sent, notified, emails = await _send_reminder_for_occurrence(session, event, reminder, occ)
                sent_count += n_sent
                all_notified.update(notified)
                pending_emails.extend(emails)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.warning("Конфликт идемпотентности напоминаний (portal), цикл пропущен")
        return 0

    for mail in pending_emails:
        mailed = await send_email(
            to=mail.to,
            subject=mail.subject,
            text_body=mail.text_body,
            html_body=mail.html_body,
        )
        if not mailed:
            continue
        session.add(
            PortalCalendarReminderSent(
                reminder_id=mail.reminder_id,
                occurrence_start=mail.occurrence_start,
                recipient_key=mail.recipient_key,
            )
        )
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            continue
        sent_count += 1

    if all_notified:
        await publish_portal_notification_updates(
            list(all_notified.keys()),
            notification_ids_by_sub=all_notified,
        )
    return sent_count


async def _already_sent(
    session: AsyncSession,
    reminder_id: object,
    occurrence_start: datetime,
    recipient_key: str,
) -> bool:
    stmt = select(PortalCalendarReminderSent.id).where(
        PortalCalendarReminderSent.reminder_id == reminder_id,
        PortalCalendarReminderSent.occurrence_start == occurrence_start,
        PortalCalendarReminderSent.recipient_key == recipient_key,
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None


async def _send_reminder_for_occurrence(
    session: AsyncSession,
    event: PortalCalendarEvent,
    reminder: PortalCalendarReminder,
    occ: Occurrence,
) -> tuple[int, dict[str, uuid.UUID], list[_PendingEmail]]:
    recipients_map: dict[str, str | None] = {f"sub:{event.organizer_sub}": event.organizer_sub}
    for att in event.attendees or []:
        if att.user_sub:
            recipients_map[f"sub:{att.user_sub}"] = att.user_sub
        else:
            recipients_map[f"email:{att.email}"] = None

    sent = 0
    portal_subs: list[str] = []
    pending_emails: list[_PendingEmail] = []
    for key, sub in recipients_map.items():
        if await _already_sent(session, reminder.id, occ.starts_at, key):
            continue
        if sub is not None:
            session.add(
                PortalCalendarReminderSent(
                    reminder_id=reminder.id,
                    occurrence_start=occ.starts_at,
                    recipient_key=key,
                )
            )
            portal_subs.append(sub)
            sent += 1
            continue
        email = key.removeprefix("email:")
        subject, text_body, html_body = reminder_email(
            event_title=occ.title,
            starts_at=occ.starts_at,
            location=occ.location,
            timezone=event.timezone,
        )
        pending_emails.append(
            _PendingEmail(
                to=email,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                reminder_id=reminder.id,
                occurrence_start=occ.starts_at,
                recipient_key=key,
            )
        )

    notified: dict[str, uuid.UUID] = {}
    if portal_subs:
        notified = await create_calendar_reminder_notifications(
            session,
            event_id=event.id,
            author_sub=event.organizer_sub,
            recipient_subs=list(dict.fromkeys(portal_subs)),
            occurrence_starts_at=occ.starts_at,
        )
    return sent, notified, pending_emails
