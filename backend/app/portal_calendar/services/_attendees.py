"""Участники событий и invite-токены."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import CalendarAttendeeStatus, CalendarInviteKind
from app.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_calendar import (
    PortalCalendarAttendee,
    PortalCalendarEvent,
    PortalCalendarInviteToken,
)
from app.portal_calendar.schemas.calendar import AttendeeRead
from app.portal_calendar.services._access import find_profiles_by_subs, require_event_access
from app.portal_calendar.services._recurrence import ensure_aware_utc
from app.portal_collab.services.notification import create_calendar_invite_notifications
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


async def ensure_organizer_attendee(
    session: AsyncSession,
    event: PortalCalendarEvent,
) -> PortalCalendarAttendee | None:
    """Гарантировать строку организатора события в attendees (без invite-уведомления)."""
    existing_stmt = select(PortalCalendarAttendee).where(
        PortalCalendarAttendee.event_id == event.id,
        PortalCalendarAttendee.user_sub == event.organizer_sub,
    )
    existing = (await session.execute(existing_stmt)).scalar_one_or_none()
    if existing is not None:
        if existing.status != CalendarAttendeeStatus.ACCEPTED.value:
            existing.status = CalendarAttendeeStatus.ACCEPTED.value
            existing.responded_at = now_utc()
        return None

    profiles = await find_profiles_by_subs(session, [event.organizer_sub])
    profile = profiles.get(event.organizer_sub)
    email = ((profile.email if profile else None) or "").strip().lower() or f"{event.organizer_sub}@portal.local"
    attendee = PortalCalendarAttendee(
        event_id=event.id,
        email=email,
        user_sub=event.organizer_sub,
        status=CalendarAttendeeStatus.ACCEPTED.value,
        responded_at=now_utc(),
    )
    session.add(attendee)
    await session.flush()
    return attendee


async def add_attendees_to_event(
    session: AsyncSession,
    organizer: UserPublic,
    event: PortalCalendarEvent,
    user_subs: list[str],
) -> tuple[list[PortalCalendarAttendee], dict[str, uuid.UUID], list[tuple[str, str, str, str]]]:
    """Добавить гостей портала по user_sub.

    Организатор допускается в списке: добавляется без invite.
    Возвращает (attendees, portal_subs_for_publish, pending_emails) —
    pending_emails пуст для портальных гостей (уведомления через portal/TG).
    """
    created: list[PortalCalendarAttendee] = []
    portal_subs: list[str] = []
    pending_mails: list[tuple[str, str, str, str]] = []

    normalized_subs = [s.strip() for s in user_subs if s.strip()]
    if not normalized_subs:
        return created, {}, pending_mails

    profiles = await find_profiles_by_subs(session, normalized_subs)
    missing = [s for s in normalized_subs if s not in profiles]
    if missing:
        raise BadRequestError(f"Пользователь портала не найден: {missing[0]}")

    existing_stmt = select(PortalCalendarAttendee).where(
        PortalCalendarAttendee.event_id == event.id,
        PortalCalendarAttendee.user_sub.in_(normalized_subs),
    )
    existing_subs = {a.user_sub for a in (await session.execute(existing_stmt)).scalars().all() if a.user_sub}

    for sub in normalized_subs:
        if sub in existing_subs:
            continue
        profile = profiles[sub]
        email = (profile.email or "").strip().lower() or f"{sub}@portal.local"
        is_organizer = sub == event.organizer_sub
        attendee = PortalCalendarAttendee(
            event_id=event.id,
            email=email,
            user_sub=profile.sub,
            status=CalendarAttendeeStatus.ACCEPTED.value,
            responded_at=now_utc(),
        )
        session.add(attendee)
        created.append(attendee)
        if not is_organizer:
            portal_subs.append(profile.sub)

    await session.flush()
    notified: dict[str, uuid.UUID] = {}
    if portal_subs:
        notified = await create_calendar_invite_notifications(
            session,
            event_id=event.id,
            author_sub=organizer.sub,
            recipient_subs=portal_subs,
            occurrence_starts_at=event.starts_at,
        )
    return created, notified, pending_mails


async def replace_event_attendees(
    session: AsyncSession,
    organizer: UserPublic,
    event: PortalCalendarEvent,
    user_subs: list[str],
) -> dict[str, uuid.UUID]:
    """Заменить список участников; организатор всегда сохраняется. Возвращает sub → notification_id."""
    normalized = list(dict.fromkeys(s.strip() for s in user_subs if s.strip()))
    if not normalized:
        raise BadRequestError("Укажите хотя бы одного участника")
    if event.organizer_sub not in normalized:
        normalized.insert(0, event.organizer_sub)

    existing = list(event.attendees or [])
    existing_by_sub = {a.user_sub: a for a in existing if a.user_sub}
    desired = set(normalized)

    for att in existing:
        if att.user_sub and att.user_sub not in desired:
            await session.delete(att)

    to_add = [s for s in normalized if s not in existing_by_sub]
    _, notified, _ = await add_attendees_to_event(session, organizer, event, to_add)
    await ensure_organizer_attendee(session, event)
    await session.flush()
    return notified


async def add_attendee(
    session: AsyncSession,
    user: UserPublic,
    event_id: uuid.UUID,
    user_sub: str,
) -> AttendeeRead:
    from app.portal_chat.services.inbox_publish import publish_portal_notification_updates

    event, _, _ = await require_event_access(session, user, event_id, write=True)
    try:
        created, notified, _pending_mails = await add_attendees_to_event(session, user, event, [user_sub])
        if not created:
            raise BadRequestError("Участник уже добавлен")
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Участник уже добавлен") from exc
    if notified:
        await publish_portal_notification_updates(list(notified.keys()), notification_ids_by_sub=notified)
    return AttendeeRead.model_validate(created[0])


async def remove_attendee(
    session: AsyncSession,
    user: UserPublic,
    event_id: uuid.UUID,
    attendee_id: uuid.UUID,
) -> None:
    event, _, _ = await require_event_access(session, user, event_id, write=True)
    attendee = await session.get(PortalCalendarAttendee, attendee_id)
    if attendee is None or attendee.event_id != event_id:
        raise NotFoundError("Участник не найден")
    if attendee.user_sub == event.organizer_sub:
        raise BadRequestError("Нельзя удалить организатора из участников")
    await session.delete(attendee)
    await session.commit()


async def accept_invite_token(
    session: AsyncSession,
    token: str,
    *,
    user: UserPublic | None = None,
) -> tuple[str, uuid.UUID | None, uuid.UUID | None]:
    stmt = select(PortalCalendarInviteToken).where(PortalCalendarInviteToken.token == token)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None or row.used_at is not None:
        raise NotFoundError("Приглашение не найдено или уже использовано")
    if ensure_aware_utc(row.expires_at) <= now_utc():
        raise BadRequestError("Срок действия приглашения истёк")

    if row.kind == CalendarInviteKind.EVENT.value:
        if row.event_id is None:
            raise BadRequestError("Некорректное приглашение")
        if user is not None:
            user_email = (user.email or "").strip().lower()
            if not user_email or user_email != row.email:
                logger.warning(
                    "Отказ в доступе к invite: user_sub=%s email=%s expected=%s",
                    user.sub,
                    user_email,
                    row.email,
                )
                raise ForbiddenError("Приглашение выдано на другой email")
        att_stmt = select(PortalCalendarAttendee).where(
            PortalCalendarAttendee.event_id == row.event_id,
            PortalCalendarAttendee.email == row.email,
        )
        attendee = (await session.execute(att_stmt)).scalar_one_or_none()
        if attendee is None:
            raise NotFoundError("Приглашение не найдено или уже использовано")
        attendee.status = CalendarAttendeeStatus.ACCEPTED.value
        attendee.responded_at = now_utc()
        if user is not None:
            attendee.user_sub = user.sub
        row.used_at = now_utc()
        await session.commit()
        return row.kind, None, row.event_id

    if row.kind == CalendarInviteKind.SHARE.value:
        from app.portal_calendar.services._sharing import accept_share_token

        calendar_id = await accept_share_token(session, row, user)
        return row.kind, calendar_id, None

    raise BadRequestError("Неизвестный тип приглашения")
