"""Legacy invite share-token (SPA-шаринг снят; peer-view — через occurrences?user_sub=)."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import CalendarMemberRole
from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_calendar import (
    PortalCalendar,
    PortalCalendarInviteToken,
    PortalCalendarMember,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


async def accept_share_token(
    session: AsyncSession,
    row: PortalCalendarInviteToken,
    user: UserPublic | None,
) -> uuid.UUID:
    if row.calendar_id is None:
        raise BadRequestError("Некорректное приглашение")
    if user is None:
        raise BadRequestError("Для принятия шаринга нужна авторизация")
    cal = await session.get(PortalCalendar, row.calendar_id)
    if cal is None:
        raise NotFoundError("Календарь не найден")

    email = (user.email or "").strip().lower()
    if not email or email != row.email:
        logger.warning(
            "Отказ в доступе к share-invite: user_sub=%s email=%s expected=%s",
            user.sub,
            email,
            row.email,
        )
        raise ForbiddenError("Приглашение выдано на другой email")

    # Явный SELECT: relationship members может быть устаревшим при expire_on_commit=False.
    match_clauses = [PortalCalendarMember.user_sub == user.sub]
    if row.email:
        match_clauses.append(PortalCalendarMember.email == row.email)
    existing = (
        await session.execute(
            select(PortalCalendarMember).where(
                PortalCalendarMember.calendar_id == row.calendar_id,
                or_(*match_clauses),
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        session.add(
            PortalCalendarMember(
                calendar_id=cal.id,
                user_sub=user.sub,
                email=row.email,
                role=row.role or CalendarMemberRole.VIEWER.value,
            )
        )
    else:
        existing.user_sub = user.sub
        if row.email:
            existing.email = row.email
    row.used_at = now_utc()
    await session.commit()
    return cal.id
