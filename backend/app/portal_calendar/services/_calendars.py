"""CRUD календарей."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import CalendarMemberRole
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_calendar import PortalCalendar, PortalCalendarMember
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_calendar.schemas.calendar import (
    CalendarCreate,
    CalendarMemberRead,
    CalendarRead,
    CalendarUpdate,
    PeerCalendarContextRead,
)
from app.portal_calendar.services._access import (
    accessible_calendar_ids,
    find_profile_by_sub,
    require_calendar_access,
    role_from_calendar,
)
from app.portal_calendar.services._realtime import publish_calendar_event
from app.schemas.auth import UserPublic


def calendar_to_read(cal: PortalCalendar, role: str) -> CalendarRead:
    members = [CalendarMemberRead.model_validate(m) for m in (cal.members or [])]
    return CalendarRead(
        id=cal.id,
        owner_sub=cal.owner_sub,
        title=cal.title,
        color=cal.color,
        timezone=cal.timezone,
        is_primary=cal.is_primary,
        my_role=role,
        created_at=cal.created_at,
        updated_at=cal.updated_at,
        members=members,
    )


async def ensure_primary_calendar(session: AsyncSession, user: UserPublic) -> PortalCalendar:
    """Идемпотентно создаёт основной календарь; безопасен при гонке (UNIQUE + IntegrityError)."""
    lookup = select(PortalCalendar).where(
        PortalCalendar.owner_sub == user.sub,
        PortalCalendar.is_primary.is_(True),
    )
    existing = (await session.execute(lookup)).scalar_one_or_none()
    if existing is not None:
        return existing
    cal = PortalCalendar(
        owner_sub=user.sub,
        title="Мой календарь",
        color="#3B82F6",
        timezone="UTC",
        is_primary=True,
    )
    session.add(cal)
    try:
        await session.flush()
        session.add(
            PortalCalendarMember(
                calendar_id=cal.id,
                user_sub=user.sub,
                email=(user.email or "").strip().lower() or None,
                role=CalendarMemberRole.OWNER.value,
            )
        )
        await session.commit()
        await session.refresh(cal, attribute_names=["members"])
        return cal
    except IntegrityError:
        await session.rollback()
        result = (await session.execute(lookup)).scalar_one_or_none()
        if result is None:
            raise
        return result


async def list_calendars(session: AsyncSession, user: UserPublic) -> list[CalendarRead]:
    await ensure_primary_calendar(session, user)
    ids = await accessible_calendar_ids(session, user)
    if not ids:
        return []
    stmt = select(PortalCalendar).where(PortalCalendar.id.in_(ids)).options(selectinload(PortalCalendar.members))
    cals = list((await session.execute(stmt)).scalars().all())
    result: list[CalendarRead] = []
    for cal in cals:
        role = role_from_calendar(cal, user) or CalendarMemberRole.VIEWER.value
        result.append(calendar_to_read(cal, role))
    result.sort(
        key=lambda c: (
            0 if c.owner_sub == user.sub else 1,
            0 if c.is_primary else 1,
            c.title.lower(),
        )
    )
    return result


async def create_calendar(session: AsyncSession, user: UserPublic, data: CalendarCreate) -> CalendarRead:
    cal = PortalCalendar(
        owner_sub=user.sub,
        title=data.title.strip(),
        color=data.color,
        timezone=data.timezone,
        is_primary=False,
    )
    session.add(cal)
    await session.flush()
    session.add(
        PortalCalendarMember(
            calendar_id=cal.id,
            user_sub=user.sub,
            email=(user.email or "").strip().lower() or None,
            role=CalendarMemberRole.OWNER.value,
        )
    )
    await session.commit()
    await session.refresh(cal, attribute_names=["members"])
    await publish_calendar_event("calendar_created", actor_sub=user.sub, calendar_id=cal.id)
    return calendar_to_read(cal, CalendarMemberRole.OWNER.value)


async def update_calendar(
    session: AsyncSession,
    user: UserPublic,
    calendar_id: uuid.UUID,
    data: CalendarUpdate,
) -> CalendarRead:
    cal, role = await require_calendar_access(session, user, calendar_id, write=True)
    if role != CalendarMemberRole.OWNER.value:
        raise ForbiddenError("Изменять настройки календаря может только владелец")
    if data.title is not None:
        cal.title = data.title.strip()
    if data.color is not None:
        cal.color = data.color
    if data.timezone is not None:
        cal.timezone = data.timezone
    cal.updated_at = now_utc()
    await session.commit()
    await session.refresh(cal, attribute_names=["members"])
    await publish_calendar_event("calendar_updated", actor_sub=user.sub, calendar_id=calendar_id)
    return calendar_to_read(cal, role)


async def delete_calendar(session: AsyncSession, user: UserPublic, calendar_id: uuid.UUID) -> None:
    cal, role = await require_calendar_access(session, user, calendar_id, write=True)
    if role != CalendarMemberRole.OWNER.value:
        raise ForbiddenError("Удалить календарь может только владелец")
    if cal.is_primary:
        raise BadRequestError("Нельзя удалить основной календарь")
    await session.delete(cal)
    await session.commit()
    await publish_calendar_event("calendar_deleted", actor_sub=user.sub, calendar_id=calendar_id)


async def get_calendar(session: AsyncSession, user: UserPublic, calendar_id: uuid.UUID) -> CalendarRead:
    cal, role = await require_calendar_access(session, user, calendar_id, write=False)
    return calendar_to_read(cal, role)


def _user_public_from_profile(profile: PortalUserProfile) -> UserPublic:
    return UserPublic(
        sub=profile.sub,
        email=profile.email or "",
        username=profile.username or "",
        full_name=profile.full_name or "",
        idp_groups=[],
        is_portal_admin=profile.is_portal_admin,
    )


async def get_peer_calendar_context(
    session: AsyncSession,
    user: UserPublic,
    peer_user_sub: str,
) -> PeerCalendarContextRead:
    """Primary-календарь коллеги для cross-create (идемпотентно создаёт primary при отсутствии)."""
    sub = peer_user_sub.strip()
    if not sub:
        raise BadRequestError("Укажите пользователя")
    if sub == user.sub:
        cal = await ensure_primary_calendar(session, user)
        return PeerCalendarContextRead(calendar_id=cal.id, owner_sub=cal.owner_sub)
    profile = await find_profile_by_sub(session, sub)
    if profile is None:
        raise NotFoundError("Пользователь не найден")
    cal = await ensure_primary_calendar(session, _user_public_from_profile(profile))
    return PeerCalendarContextRead(calendar_id=cal.id, owner_sub=cal.owner_sub)
