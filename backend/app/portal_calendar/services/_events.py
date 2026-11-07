"""CRUD событий и развёртка в окне дат."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError, NotFoundError
from app.core.optimistic_lock import compare_and_swap_row
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_calendar import (
    PortalCalendar,
    PortalCalendarEvent,
    PortalCalendarEventOverride,
    PortalCalendarReminder,
)
from app.infrastructure.email.smtp import send_email
from app.portal_calendar.schemas.calendar import (
    AttendeeRead,
    EventCreate,
    EventOccurrenceOverride,
    EventOccurrenceRead,
    EventRead,
    EventUpdate,
    ReminderRead,
)
from app.portal_calendar.services._access import (
    accessible_calendar_ids,
    accessible_event_ids_as_attendee,
    find_profile_by_sub,
    peer_attendee_event_ids_visible_to_viewer,
    require_calendar_create_access,
    require_event_access,
)
from app.portal_calendar.services._attendees import (
    add_attendees_to_event,
    ensure_organizer_attendee,
    replace_event_attendees,
)
from app.portal_calendar.services._realtime import publish_calendar_event
from app.portal_calendar.services._recurrence import (
    Occurrence,
    ensure_aware_utc,
    expand_event_occurrences,
    validate_rrule,
)
from app.portal_collab.services.notification import (
    create_calendar_event_cancelled_notifications,
    create_calendar_event_updated_notifications,
    delete_calendar_event_pre_cancel_notifications,
)
from app.schemas.auth import UserPublic

# Лимиты окна развёртки (api-pagination / performance)
_MAX_OCCURRENCE_WINDOW = timedelta(days=93)
_MAX_OCCURRENCES = 2000


def _validate_event_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned:
        raise BadRequestError("Укажите название события")
    return cleaned


def event_to_read(event: PortalCalendarEvent) -> EventRead:
    attendees = [AttendeeRead.model_validate(a) for a in (event.attendees or [])]
    reminders = [ReminderRead.model_validate(r) for r in (event.reminders or [])]
    return EventRead(
        id=event.id,
        calendar_id=event.calendar_id,
        organizer_sub=event.organizer_sub,
        title=event.title,
        description=event.description,
        location=event.location,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        timezone=event.timezone,
        rrule=event.rrule,
        color=event.color,
        version=getattr(event, "version", 1) or 1,
        created_at=event.created_at,
        updated_at=event.updated_at,
        attendees=attendees,
        reminders=reminders,
    )


def occurrence_to_read(
    occ: Occurrence,
    calendar: PortalCalendar,
    *,
    is_peer_view: bool = False,
) -> EventOccurrenceRead:
    return EventOccurrenceRead(
        event_id=occ.event.id,
        calendar_id=calendar.id,
        calendar_color=calendar.color,
        color=occ.event.color,
        original_start=occ.original_start,
        starts_at=occ.starts_at,
        ends_at=occ.ends_at,
        title=occ.title,
        description=occ.description,
        location=occ.location,
        timezone=occ.event.timezone,
        rrule=occ.event.rrule,
        organizer_sub=occ.event.organizer_sub,
        is_cancelled=occ.is_cancelled,
        is_peer_view=is_peer_view,
        attendees=[AttendeeRead.model_validate(a) for a in (occ.event.attendees or [])],
        reminders=[ReminderRead.model_validate(r) for r in (occ.event.reminders or [])],
    )


async def create_event(session: AsyncSession, user: UserPublic, data: EventCreate) -> EventRead:
    from app.portal_chat.services.inbox_publish import publish_portal_notification_updates

    cal, _ = await require_calendar_create_access(session, user, data.calendar_id)
    title = _validate_event_title(data.title)
    if not data.attendees:
        raise BadRequestError("Укажите хотя бы одного участника")
    starts = ensure_aware_utc(data.starts_at)
    ends = ensure_aware_utc(data.ends_at) if data.ends_at is not None else None
    if ends is not None and ends <= starts:
        raise BadRequestError("Окончание события должно быть позже начала")
    event = PortalCalendarEvent(
        calendar_id=data.calendar_id,
        organizer_sub=user.sub,
        title=title,
        description=data.description,
        location=data.location,
        starts_at=starts,
        ends_at=ends,
        timezone=data.timezone,
        rrule=validate_rrule(data.rrule, starts) if data.rrule else None,
        color=data.color,
    )
    session.add(event)
    await session.flush()
    for rem in data.reminders:
        session.add(
            PortalCalendarReminder(
                event_id=event.id,
                offset_minutes=rem.offset_minutes,
                channel=rem.channel.value,
            )
        )
    notified: dict[str, uuid.UUID] = {}
    pending_mails: list[tuple[str, str, str, str]] = []
    attendee_subs = [a.user_sub for a in data.attendees]
    _, notified, pending_mails = await add_attendees_to_event(session, user, event, attendee_subs)
    if cal.owner_sub == user.sub or user.sub in attendee_subs:
        await ensure_organizer_attendee(session, event)
    await session.commit()
    for to, subject, text_body, html_body in pending_mails:
        await send_email(to=to, subject=subject, text_body=text_body, html_body=html_body)
    if notified:
        await publish_portal_notification_updates(list(notified.keys()), notification_ids_by_sub=notified)
    event, _, _ = await require_event_access(session, user, event.id, write=False)
    await publish_calendar_event(
        "event_created",
        actor_sub=user.sub,
        calendar_id=event.calendar_id,
        event_id=event.id,
    )
    return event_to_read(event)


async def get_event(session: AsyncSession, user: UserPublic, event_id: uuid.UUID) -> EventRead:
    event, _, _ = await require_event_access(session, user, event_id, write=False)
    return event_to_read(event)


def _event_notify_fingerprint(event: PortalCalendarEvent) -> tuple[object, ...]:
    """Поля, изменение которых стоит уведомления участникам (без color)."""
    return (
        event.title,
        event.description or "",
        event.location or "",
        event.starts_at,
        event.ends_at,
        event.timezone,
        event.rrule or "",
        tuple(sorted(r.offset_minutes for r in (event.reminders or []))),
        tuple(sorted((a.user_sub or "") for a in (event.attendees or []) if a.user_sub)),
    )


async def update_event(
    session: AsyncSession,
    user: UserPublic,
    event_id: uuid.UUID,
    data: EventUpdate,
) -> EventRead:
    from app.portal_chat.services.inbox_publish import publish_portal_notification_updates

    event, _, _ = await require_event_access(session, user, event_id, write=True)
    fp_before = _event_notify_fingerprint(event)

    patch = data.model_dump(exclude_unset=True)
    patch.pop("expected_version", None)
    has_side = data.reminders is not None or data.attendees is not None
    values: dict[str, Any] = {"updated_at": now_utc()}

    if data.title is not None:
        values["title"] = _validate_event_title(data.title)
    if data.description is not None:
        values["description"] = data.description
    if data.location is not None:
        values["location"] = data.location
    if data.starts_at is not None:
        values["starts_at"] = ensure_aware_utc(data.starts_at)
    if "ends_at" in data.model_fields_set:
        values["ends_at"] = ensure_aware_utc(data.ends_at) if data.ends_at is not None else None
    if data.timezone is not None:
        values["timezone"] = data.timezone
    if "rrule" in data.model_fields_set:
        starts_for_rrule = values.get("starts_at", event.starts_at)
        values["rrule"] = validate_rrule(data.rrule, starts_for_rrule) if data.rrule else None
    if "color" in data.model_fields_set:
        values["color"] = data.color

    next_starts = values.get("starts_at", event.starts_at)
    next_ends = values["ends_at"] if "ends_at" in values else event.ends_at
    if next_ends is not None and ensure_aware_utc(next_ends) <= ensure_aware_utc(next_starts):
        raise BadRequestError("Окончание события должно быть позже начала")

    if set(values.keys()) == {"updated_at"} and not has_side:
        return event_to_read(event)

    new_version = await compare_and_swap_row(
        session,
        PortalCalendarEvent,
        entity_id=event_id,
        expected_version=data.expected_version,
        values=values,
        conflict_message="Событие календаря изменено другим пользователем",
    )
    await session.refresh(event)
    event.version = new_version

    notified: dict[str, uuid.UUID] = {}
    if data.reminders is not None:
        await session.execute(delete(PortalCalendarReminder).where(PortalCalendarReminder.event_id == event.id))
        for rem in data.reminders:
            session.add(
                PortalCalendarReminder(
                    event_id=event.id,
                    offset_minutes=rem.offset_minutes,
                    channel=rem.channel.value,
                )
            )
        await session.flush()
        await session.refresh(event, attribute_names=["reminders"])
    if data.attendees is not None:
        notified = await replace_event_attendees(
            session,
            user,
            event,
            [a.user_sub for a in data.attendees],
        )
        await session.refresh(event, attribute_names=["attendees"])

    fp_after = _event_notify_fingerprint(event)
    updated_by_sub: dict[str, uuid.UUID] = {}
    if fp_before != fp_after:
        recipient_subs = [a.user_sub for a in (event.attendees or []) if a.user_sub and a.user_sub != user.sub]
        updated_by_sub = await create_calendar_event_updated_notifications(
            session,
            event_id=event.id,
            author_sub=user.sub,
            recipient_subs=recipient_subs,
            occurrence_starts_at=event.starts_at,
        )
    ids_by_sub = {**notified, **updated_by_sub}
    await session.commit()
    if ids_by_sub:
        await publish_portal_notification_updates(
            list(ids_by_sub.keys()),
            notification_ids_by_sub=ids_by_sub,
        )
    event, _, _ = await require_event_access(session, user, event_id, write=False)
    await publish_calendar_event(
        "event_updated",
        actor_sub=user.sub,
        calendar_id=event.calendar_id,
        event_id=event.id,
    )
    return event_to_read(event)


async def delete_event(session: AsyncSession, user: UserPublic, event_id: uuid.UUID) -> None:
    from app.portal_chat.services.inbox_publish import publish_portal_notification_updates

    event, _, _ = await require_event_access(session, user, event_id, write=True)
    calendar_id = event.calendar_id
    title = event.title
    recipient_subs = [a.user_sub for a in (event.attendees or []) if a.user_sub and a.user_sub != user.sub]
    notified = await create_calendar_event_cancelled_notifications(
        session,
        event_id=event.id,
        author_sub=user.sub,
        recipient_subs=recipient_subs,
        context_title=title,
    )
    await delete_calendar_event_pre_cancel_notifications(session, event_id)
    await session.delete(event)
    await session.commit()
    if notified:
        await publish_portal_notification_updates(
            list(notified.keys()),
            notification_ids_by_sub=notified,
        )
    await publish_calendar_event(
        "event_deleted",
        actor_sub=user.sub,
        calendar_id=calendar_id,
        event_id=event_id,
    )


async def upsert_occurrence_override(
    session: AsyncSession,
    user: UserPublic,
    event_id: uuid.UUID,
    data: EventOccurrenceOverride,
) -> EventRead:
    from app.portal_chat.services.inbox_publish import publish_portal_notification_updates

    event, _, _ = await require_event_access(session, user, event_id, write=True)
    if data.starts_at is not None and data.ends_at is not None and data.ends_at <= data.starts_at:
        raise BadRequestError("Окончание события должно быть позже начала")
    stmt = select(PortalCalendarEventOverride).where(
        PortalCalendarEventOverride.event_id == event_id,
        PortalCalendarEventOverride.original_start == data.original_start,
    )
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is None:
        existing = PortalCalendarEventOverride(
            event_id=event_id,
            original_start=data.original_start,
        )
        session.add(existing)
    existing.starts_at = data.starts_at
    existing.ends_at = data.ends_at
    existing.title = data.title
    existing.description = data.description
    existing.location = data.location
    existing.is_cancelled = data.is_cancelled
    event.updated_at = now_utc()
    recipient_subs = [a.user_sub for a in (event.attendees or []) if a.user_sub and a.user_sub != user.sub]
    notified = await create_calendar_event_updated_notifications(
        session,
        event_id=event.id,
        author_sub=user.sub,
        recipient_subs=recipient_subs,
        occurrence_starts_at=data.starts_at or event.starts_at,
    )
    await session.commit()
    if notified:
        await publish_portal_notification_updates(
            list(notified.keys()),
            notification_ids_by_sub=notified,
        )
    await publish_calendar_event(
        "event_updated",
        actor_sub=user.sub,
        calendar_id=event.calendar_id,
        event_id=event.id,
    )
    return await get_event(session, user, event_id)


def _validate_occurrence_window(window_start: datetime, window_end: datetime) -> tuple[datetime, datetime]:
    window_start = ensure_aware_utc(window_start)
    window_end = ensure_aware_utc(window_end)
    if window_end <= window_start:
        raise BadRequestError("Некорректное окно дат")
    if window_end - window_start > _MAX_OCCURRENCE_WINDOW:
        raise BadRequestError("Окно дат не должно превышать 93 дня")
    return window_start, window_end


async def _load_events_for_calendar_ids(
    session: AsyncSession,
    calendar_ids: list[uuid.UUID],
    extra_event_ids: list[uuid.UUID],
    window_start: datetime,
    window_end: datetime,
) -> list[PortalCalendarEvent]:
    event_filters = []
    if calendar_ids:
        event_filters.append(PortalCalendarEvent.calendar_id.in_(calendar_ids))
    if extra_event_ids:
        event_filters.append(PortalCalendarEvent.id.in_(extra_event_ids))
    if not event_filters:
        return []

    effective_end = func.coalesce(PortalCalendarEvent.ends_at, PortalCalendarEvent.starts_at)
    stmt = (
        select(PortalCalendarEvent)
        .where(or_(*event_filters))
        .where(
            or_(
                PortalCalendarEvent.rrule.is_not(None),
                ((PortalCalendarEvent.starts_at < window_end) & (effective_end > window_start)),
            )
        )
        .options(
            selectinload(PortalCalendarEvent.attendees),
            selectinload(PortalCalendarEvent.reminders),
            selectinload(PortalCalendarEvent.overrides),
            selectinload(PortalCalendarEvent.calendar),
        )
    )
    return list((await session.execute(stmt)).scalars().all())


def _expand_to_reads(
    events: list[PortalCalendarEvent],
    window_start: datetime,
    window_end: datetime,
    *,
    is_peer_view: bool,
    result: list[EventOccurrenceRead],
    seen: set[tuple[uuid.UUID, datetime]],
) -> bool:
    """Добавляет occurrences в result. True — достигнут cap."""
    for event in events:
        cal = event.calendar
        if cal is None:
            continue
        for occ in expand_event_occurrences(event, window_start, window_end):
            if occ.is_cancelled:
                continue
            key = (occ.event.id, occ.original_start)
            if key in seen:
                continue
            seen.add(key)
            result.append(occurrence_to_read(occ, cal, is_peer_view=is_peer_view))
            if len(result) >= _MAX_OCCURRENCES:
                return True
    return False


async def list_occurrences(
    session: AsyncSession,
    user: UserPublic,
    *,
    window_start: datetime,
    window_end: datetime,
    calendar_ids: list[uuid.UUID] | None = None,
    peer_user_sub: str | None = None,
) -> list[EventOccurrenceRead]:
    window_start, window_end = _validate_occurrence_window(window_start, window_end)

    result: list[EventOccurrenceRead] = []
    seen: set[tuple[uuid.UUID, datetime]] = set()

    peer_sub = (peer_user_sub or "").strip()
    if peer_sub and peer_sub != user.sub:
        profile = await find_profile_by_sub(session, peer_sub)
        if profile is None:
            raise NotFoundError("Пользователь не найден")
        peer_cal_stmt = select(PortalCalendar).where(PortalCalendar.owner_sub == peer_sub)
        peer_calendars = list((await session.execute(peer_cal_stmt)).scalars().all())
        peer_cal_ids = [c.id for c in peer_calendars]
        extra_ids = await peer_attendee_event_ids_visible_to_viewer(
            session,
            user,
            peer_sub=peer_sub,
            peer_email=profile.email,
            peer_owned_calendar_ids=peer_cal_ids,
        )
        if peer_cal_ids or extra_ids:
            peer_events = await _load_events_for_calendar_ids(
                session, peer_cal_ids, extra_ids, window_start, window_end
            )
            _expand_to_reads(
                peer_events,
                window_start,
                window_end,
                is_peer_view=True,
                result=result,
                seen=seen,
            )
        result.sort(key=lambda o: o.starts_at)
        return result

    allowed = set(await accessible_calendar_ids(session, user))
    if calendar_ids:
        ids = [cid for cid in calendar_ids if cid in allowed]
    else:
        ids = list(allowed)

    owned_ids = set(
        (await session.execute(select(PortalCalendar.id).where(PortalCalendar.owner_sub == user.sub))).scalars().all()
    )
    exclude_from_attendee_extra = set(ids) | owned_ids

    attendee_event_ids = await accessible_event_ids_as_attendee(session, user)
    if attendee_event_ids and exclude_from_attendee_extra:
        external_stmt = select(PortalCalendarEvent.id).where(
            PortalCalendarEvent.id.in_(attendee_event_ids),
            PortalCalendarEvent.calendar_id.notin_(list(exclude_from_attendee_extra)),
        )
        attendee_event_ids = list((await session.execute(external_stmt)).scalars().all())
    elif attendee_event_ids and not exclude_from_attendee_extra:
        pass
    else:
        attendee_event_ids = []

    own_events = await _load_events_for_calendar_ids(session, ids, attendee_event_ids, window_start, window_end)
    _expand_to_reads(own_events, window_start, window_end, is_peer_view=False, result=result, seen=seen)

    result.sort(key=lambda o: o.starts_at)
    return result
