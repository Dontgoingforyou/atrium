"""Поиск событий календаря."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.text_search import escape_ilike_pattern
from app.infrastructure.db.models.portal_calendar import PortalCalendarEvent
from app.portal_calendar.services._access import accessible_calendar_ids, accessible_event_ids_as_attendee
from app.schemas.auth import UserPublic


@dataclass(frozen=True, slots=True)
class CalendarEventSearchHit:
    id: uuid.UUID
    calendar_id: uuid.UUID
    title: str
    starts_at: datetime
    ends_at: datetime | None
    calendar_title: str
    location: str | None


async def search_events(
    session: AsyncSession,
    user: UserPublic,
    q: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[CalendarEventSearchHit], int]:
    """ILIKE по title/description/location среди доступных календарей и attendee-событий."""
    pattern = f"%{escape_ilike_pattern(q.strip().lower())}%"
    allowed = set(await accessible_calendar_ids(session, user))
    attendee_event_ids = await accessible_event_ids_as_attendee(session, user)

    event_filters = []
    if allowed:
        event_filters.append(PortalCalendarEvent.calendar_id.in_(allowed))
    if attendee_event_ids:
        event_filters.append(PortalCalendarEvent.id.in_(attendee_event_ids))
    if not event_filters:
        return [], 0

    text_match = or_(
        func.lower(PortalCalendarEvent.title).like(pattern, escape="\\"),
        func.lower(func.coalesce(PortalCalendarEvent.description, "")).like(pattern, escape="\\"),
        func.lower(func.coalesce(PortalCalendarEvent.location, "")).like(pattern, escape="\\"),
    )
    base = (
        select(PortalCalendarEvent)
        .where(or_(*event_filters))
        .where(text_match)
        .options(selectinload(PortalCalendarEvent.calendar))
    )
    count_stmt = select(func.count()).select_from(
        select(PortalCalendarEvent.id).where(or_(*event_filters)).where(text_match).subquery()
    )
    total = int(await session.scalar(count_stmt) or 0)
    stmt = base.order_by(PortalCalendarEvent.starts_at.desc()).offset(skip).limit(limit)
    rows = list((await session.execute(stmt)).scalars().all())
    hits: list[CalendarEventSearchHit] = []
    for ev in rows:
        cal_title = ev.calendar.title if ev.calendar is not None else ""
        hits.append(
            CalendarEventSearchHit(
                id=ev.id,
                calendar_id=ev.calendar_id,
                title=ev.title,
                starts_at=ev.starts_at,
                ends_at=ev.ends_at,
                calendar_title=cal_title,
                location=ev.location,
            )
        )
    return hits, total


async def accessible_calendar_event_ids(
    session: AsyncSession,
    user: UserPublic,
    event_ids: list[uuid.UUID],
) -> set[uuid.UUID]:
    """Подмножество event_ids, видимых пользователю (календарь или attendee)."""
    if not event_ids:
        return set()
    allowed = set(await accessible_calendar_ids(session, user))
    attendee_ids = set(await accessible_event_ids_as_attendee(session, user))
    visible: set[uuid.UUID] = {eid for eid in event_ids if eid in attendee_ids}
    remaining = [eid for eid in event_ids if eid not in visible]
    if not remaining:
        return visible
    visibility = [PortalCalendarEvent.organizer_sub == user.sub]
    if allowed:
        visibility.append(PortalCalendarEvent.calendar_id.in_(allowed))
    rows = (
        (
            await session.execute(
                select(PortalCalendarEvent.id).where(
                    PortalCalendarEvent.id.in_(remaining),
                    or_(*visibility),
                )
            )
        )
        .scalars()
        .all()
    )
    visible.update(rows)
    return visible
