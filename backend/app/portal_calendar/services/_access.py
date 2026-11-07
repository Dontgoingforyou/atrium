"""Права доступа к календарям и событиям."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import ColumnElement, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import CalendarMemberRole
from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_calendar import (
    PortalCalendar,
    PortalCalendarAttendee,
    PortalCalendarEvent,
    PortalCalendarMember,
)
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

_WRITE_ROLES = frozenset({CalendarMemberRole.OWNER.value, CalendarMemberRole.EDITOR.value})
_ATTENDEE_READ_ROLE = "attendee"
_PEER_CREATE_ROLE = "peer_create"
_ORGANIZER_ROLE = "organizer"


def _member_match_clause(user: UserPublic) -> ColumnElement[bool]:
    email = (user.email or "").strip().lower()
    clauses: list[ColumnElement[bool]] = [PortalCalendarMember.user_sub == user.sub]
    if email:
        clauses.append(PortalCalendarMember.email == email)
    return or_(*clauses)


def _is_event_attendee(event: PortalCalendarEvent, user: UserPublic) -> bool:
    email = (user.email or "").strip().lower()
    for a in event.attendees or []:
        if a.user_sub == user.sub:
            return True
        if email and a.email == email:
            return True
    return False


def role_from_calendar(cal: PortalCalendar, user: UserPublic) -> str | None:
    """Роль из уже загруженного календаря (без доп. запроса)."""
    if cal.owner_sub == user.sub:
        return CalendarMemberRole.OWNER.value
    email = (user.email or "").strip().lower()
    for m in cal.members or []:
        if m.user_sub == user.sub or (email and m.email == email):
            return m.role
    return None


async def resolve_calendar_role(
    session: AsyncSession,
    user: UserPublic,
    cal: PortalCalendar,
) -> str | None:
    """Роль по owner_sub / строке member в БД (не через кэш relationship)."""
    if cal.owner_sub == user.sub:
        return CalendarMemberRole.OWNER.value
    stmt = (
        select(PortalCalendarMember.role)
        .where(
            PortalCalendarMember.calendar_id == cal.id,
            _member_match_clause(user),
        )
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def find_profile_by_sub(session: AsyncSession, user_sub: str) -> PortalUserProfile | None:
    sub = user_sub.strip()
    if not sub:
        return None
    stmt = select(PortalUserProfile).where(PortalUserProfile.sub == sub)
    return (await session.execute(stmt)).scalar_one_or_none()


async def find_profiles_by_subs(
    session: AsyncSession,
    user_subs: list[str],
) -> dict[str, PortalUserProfile]:
    subs = [s.strip() for s in user_subs if s.strip()]
    if not subs:
        return {}
    stmt = select(PortalUserProfile).where(PortalUserProfile.sub.in_(subs))
    rows = list((await session.execute(stmt)).scalars().all())
    return {p.sub: p for p in rows}


async def get_calendar_role(
    session: AsyncSession,
    user: UserPublic,
    calendar_id: uuid.UUID,
) -> str | None:
    cal = await session.get(PortalCalendar, calendar_id)
    if cal is None:
        return None
    return await resolve_calendar_role(session, user, cal)


async def require_calendar_create_access(
    session: AsyncSession,
    user: UserPublic,
    calendar_id: uuid.UUID,
) -> tuple[PortalCalendar, str]:
    """Create: owner/editor/legacy member или cross-create в owned-календарь коллеги."""
    cal = await session.get(
        PortalCalendar,
        calendar_id,
        options=[selectinload(PortalCalendar.members)],
        populate_existing=True,
    )
    if cal is None:
        raise NotFoundError("Календарь не найден")
    role = await resolve_calendar_role(session, user, cal)
    if role in _WRITE_ROLES:
        return cal, role
    if role == CalendarMemberRole.VIEWER.value:
        logger.warning(
            "Отказ в доступе (create): user_sub=%s resource=calendar/%s role=%s",
            user.sub,
            calendar_id,
            role,
        )
        raise ForbiddenError("Недостаточно прав для изменения календаря")
    if role is None and cal.owner_sub != user.sub:
        owner_profile = await find_profile_by_sub(session, cal.owner_sub)
        if owner_profile is None:
            raise NotFoundError("Календарь не найден")
        return cal, _PEER_CREATE_ROLE
    logger.warning(
        "Отказ в доступе (create): user_sub=%s resource=calendar/%s",
        user.sub,
        calendar_id,
    )
    raise ForbiddenError("Нет доступа к календарю")


async def require_calendar_access(
    session: AsyncSession,
    user: UserPublic,
    calendar_id: uuid.UUID,
    *,
    write: bool = False,
) -> tuple[PortalCalendar, str]:
    cal = await session.get(
        PortalCalendar,
        calendar_id,
        options=[selectinload(PortalCalendar.members)],
        populate_existing=True,
    )
    if cal is None:
        raise NotFoundError("Календарь не найден")
    role = await resolve_calendar_role(session, user, cal)
    if role is None:
        logger.warning(
            "Отказ в доступе: user_sub=%s resource=calendar/%s",
            user.sub,
            calendar_id,
        )
        raise ForbiddenError("Нет доступа к календарю")
    if write and role not in _WRITE_ROLES:
        logger.warning(
            "Отказ в доступе (write): user_sub=%s resource=calendar/%s role=%s",
            user.sub,
            calendar_id,
            role,
        )
        raise ForbiddenError("Недостаточно прав для изменения календаря")
    return cal, role


async def require_event_access(
    session: AsyncSession,
    user: UserPublic,
    event_id: uuid.UUID,
    *,
    write: bool = False,
) -> tuple[PortalCalendarEvent, PortalCalendar, str]:
    """Доступ: член календаря; организатор читает и пишет; иначе чтение для attendee."""
    stmt = (
        select(PortalCalendarEvent)
        .where(PortalCalendarEvent.id == event_id)
        .options(
            selectinload(PortalCalendarEvent.attendees),
            selectinload(PortalCalendarEvent.reminders),
            selectinload(PortalCalendarEvent.overrides),
            selectinload(PortalCalendarEvent.calendar).selectinload(PortalCalendar.members),
        )
        .execution_options(populate_existing=True)
    )
    event = (await session.execute(stmt)).scalar_one_or_none()
    if event is None:
        raise NotFoundError("Событие не найдено")

    cal = event.calendar
    if cal is None:
        cal = await session.get(
            PortalCalendar,
            event.calendar_id,
            options=[selectinload(PortalCalendar.members)],
            populate_existing=True,
        )
        if cal is None:
            raise NotFoundError("Календарь не найден")

    role = await resolve_calendar_role(session, user, cal)
    if event.organizer_sub == user.sub:
        return event, cal, role if role is not None else _ORGANIZER_ROLE
    if role is not None:
        if write and role not in _WRITE_ROLES:
            logger.warning(
                "Отказ в доступе (write): user_sub=%s resource=calendar_event/%s role=%s",
                user.sub,
                event_id,
                role,
            )
            raise ForbiddenError("Недостаточно прав для изменения события")
        return event, cal, role

    if not write and _is_event_attendee(event, user):
        return event, cal, _ATTENDEE_READ_ROLE

    logger.warning(
        "Отказ в доступе: user_sub=%s resource=calendar_event/%s",
        user.sub,
        event_id,
    )
    raise ForbiddenError("Нет доступа к событию")


async def accessible_calendar_ids(session: AsyncSession, user: UserPublic) -> list[uuid.UUID]:
    owned = select(PortalCalendar.id).where(PortalCalendar.owner_sub == user.sub)
    shared = select(PortalCalendarMember.calendar_id).where(_member_match_clause(user))
    rows = (await session.execute(owned.union(shared))).scalars().all()
    return list(rows)


async def event_ids_for_attendee_identity(
    session: AsyncSession,
    *,
    user_sub: str,
    email: str | None,
) -> list[uuid.UUID]:
    """События, где sub/email — строка attendee (без проверки членства в календаре)."""
    email_norm = (email or "").strip().lower()
    clauses = [PortalCalendarAttendee.user_sub == user_sub]
    if email_norm:
        clauses.append(PortalCalendarAttendee.email == email_norm)
    stmt = select(PortalCalendarAttendee.event_id).where(or_(*clauses))
    return list((await session.execute(stmt)).scalars().all())


async def accessible_event_ids_as_attendee(session: AsyncSession, user: UserPublic) -> list[uuid.UUID]:
    """События, где пользователь — гость (для list occurrences без членства в календаре)."""
    return await event_ids_for_attendee_identity(session, user_sub=user.sub, email=user.email)


async def peer_attendee_event_ids_visible_to_viewer(
    session: AsyncSession,
    viewer: UserPublic,
    *,
    peer_sub: str,
    peer_email: str | None,
    peer_owned_calendar_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    """Приглашения коллеги, которые viewer сам может читать.

    Доступ как у get/list: организатор, член календаря или attendee.
    """
    peer_ids = await event_ids_for_attendee_identity(session, user_sub=peer_sub, email=peer_email)
    if not peer_ids:
        return []
    viewer_cal_ids = set(await accessible_calendar_ids(session, viewer))
    viewer_attendee_ids = set(await accessible_event_ids_as_attendee(session, viewer))
    stmt = select(
        PortalCalendarEvent.id,
        PortalCalendarEvent.calendar_id,
        PortalCalendarEvent.organizer_sub,
    ).where(PortalCalendarEvent.id.in_(peer_ids))
    if peer_owned_calendar_ids:
        stmt = stmt.where(PortalCalendarEvent.calendar_id.notin_(peer_owned_calendar_ids))
    visible: list[uuid.UUID] = []
    for event_id, calendar_id, organizer_sub in (await session.execute(stmt)).all():
        if organizer_sub == viewer.sub or calendar_id in viewer_cal_ids or event_id in viewer_attendee_ids:
            visible.append(event_id)
    return visible
