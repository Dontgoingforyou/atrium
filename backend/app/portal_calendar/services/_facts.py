"""Уведомление портала по одному факту календаря."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import now_utc
from app.infrastructure.db.models.portal_calendar_fact import PortalCalendarFact
from app.portal_collab.services._notification_create import (
    create_calendar_event_cancelled_notifications,
    create_calendar_event_updated_notifications,
    create_calendar_invite_notifications,
)

_KIND_CREATED = "event_created"
_KIND_UPDATED = "event_updated"
_KIND_DELETED = "event_deleted"


def _uuid(value: object, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Факт календаря без {field}") from exc


def _starts_at(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


def _subs(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item]


async def apply_calendar_fact(session: AsyncSession, body: dict[str, object]) -> dict[str, uuid.UUID]:
    """Получатель → id уведомления. Повтор fact_id возвращает пустой словарь."""
    fact_id = _uuid(body.get("fact_id"), "fact_id")
    if await session.get(PortalCalendarFact, fact_id) is not None:
        return {}
    event_id = _uuid(body.get("event_id"), "event_id")
    kind = str(body.get("kind") or "")[:32]
    session.add(
        PortalCalendarFact(
            fact_id=fact_id,
            event_id=event_id,
            kind=kind or "unknown",
            consumed_at=now_utc(),
        )
    )
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return {}

    organizer = str(body.get("organizer_sub") or "")
    title = str(body.get("title") or "")
    starts = _starts_at(body.get("starts_at"))
    recipients = _subs(body.get("attendee_subs"))
    if not organizer or not recipients:
        return {}
    if kind == _KIND_CREATED:
        return await create_calendar_invite_notifications(
            session,
            event_id=event_id,
            author_sub=organizer,
            recipient_subs=recipients,
            occurrence_starts_at=starts,
            context_title=title,
        )
    if kind == _KIND_UPDATED:
        return await create_calendar_event_updated_notifications(
            session,
            event_id=event_id,
            author_sub=organizer,
            recipient_subs=recipients,
            occurrence_starts_at=starts,
            context_title=title,
        )
    if kind == _KIND_DELETED:
        return await create_calendar_event_cancelled_notifications(
            session,
            event_id=event_id,
            author_sub=organizer,
            recipient_subs=recipients,
            context_title=title,
        )
    return {}
