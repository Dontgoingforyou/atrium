"""Подпись владельца календаря из профиля портала (в т.ч. test.* вне справочника)."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_constants import SSO_GID_OUTSTAFF, normalize_sso_gid_number
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_calendar.schemas.calendar import CalendarRead

_OUTSTAFF_DEPARTMENT_LABEL = "Аутстафф"
_NO_DEPARTMENT_LABEL = "Без отдела"


def _label(profile: PortalUserProfile) -> str:
    for value in (profile.full_name, profile.email, profile.username):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return profile.sub


def department_of(gid_number: str | None) -> tuple[str | None, str]:
    """Отдел владельца: известное имя только у Аутстаффа, остальные gid — как номер."""
    gid = normalize_sso_gid_number(gid_number)
    if gid is None:
        return None, _NO_DEPARTMENT_LABEL
    if gid == SSO_GID_OUTSTAFF:
        return gid, _OUTSTAFF_DEPARTMENT_LABEL
    return gid, gid


async def _profiles_by_sub(
    session: AsyncSession,
    subs: set[str],
) -> dict[str, PortalUserProfile]:
    if not subs:
        return {}
    rows = await session.scalars(select(PortalUserProfile).where(PortalUserProfile.sub.in_(subs)))
    return {profile.sub: profile for profile in rows}


async def with_owner_labels(session: AsyncSession, calendars: Iterable[CalendarRead]) -> list[CalendarRead]:
    rows = list(calendars)
    profiles = await _profiles_by_sub(session, {item.owner_sub for item in rows if item.owner_sub})
    enriched: list[CalendarRead] = []
    for item in rows:
        profile = profiles.get(item.owner_sub)
        enriched.append(item.model_copy(update={"owner_label": _label(profile) if profile is not None else None}))
    return enriched


async def with_owner_label(session: AsyncSession, calendar: CalendarRead) -> CalendarRead:
    return (await with_owner_labels(session, [calendar]))[0]


async def with_departments(session: AsyncSession, calendars: Iterable[CalendarRead]) -> list[CalendarRead]:
    """Подпись владельца и отдел одним чтением профилей."""
    rows = list(calendars)
    profiles = await _profiles_by_sub(session, {item.owner_sub for item in rows if item.owner_sub})
    enriched: list[CalendarRead] = []
    for item in rows:
        profile = profiles.get(item.owner_sub)
        department_id, department_label = department_of(profile.gid_number if profile is not None else None)
        enriched.append(
            item.model_copy(
                update={
                    "owner_label": _label(profile) if profile is not None else None,
                    "department_id": department_id,
                    "department_label": department_label,
                }
            )
        )
    return enriched
