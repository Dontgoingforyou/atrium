"""Один факт — одно уведомление, повтор счётчик не увеличивает."""

from __future__ import annotations

import uuid

import pytest
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.portal_calendar.services._facts import apply_calendar_fact
from app.portal_collab.services._notification_access import NOTIFICATION_TYPE_CALENDAR_INVITE
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


def _fact() -> dict[str, object]:
    return {
        "fact_id": str(uuid.uuid4()),
        "kind": "event_created",
        "event_id": str(uuid.uuid4()),
        "organizer_sub": "organizer",
        "title": "Планёрка",
        "starts_at": "2026-10-29T12:00:00+00:00",
        "attendee_subs": ["organizer", "guest"],
    }


async def _invite_count(session: AsyncSession) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(PortalNotification)
            .where(PortalNotification.type == NOTIFICATION_TYPE_CALENDAR_INVITE)
        )
        or 0
    )


@pytest.mark.asyncio
async def test_repeat_fact_does_not_add_a_notification(sqlite_session: AsyncSession) -> None:
    body = _fact()
    first = await apply_calendar_fact(sqlite_session, body)
    await sqlite_session.commit()
    assert set(first) == {"guest"}
    assert await _invite_count(sqlite_session) == 1

    second = await apply_calendar_fact(sqlite_session, body)
    await sqlite_session.commit()
    assert second == {}
    assert await _invite_count(sqlite_session) == 1
