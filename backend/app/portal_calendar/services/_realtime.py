"""Публикация real-time событий календаря."""

from __future__ import annotations

import logging
import uuid

from app.infrastructure.ws.managers import get_calendar_manager
from app.infrastructure.ws.room_manager import CALENDAR_ROOM_ID

logger = logging.getLogger(__name__)


async def publish_calendar_event(
    event_type: str,
    *,
    actor_sub: str,
    calendar_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
) -> None:
    """Публикует событие в глобальный WS-канал календаря (best-effort)."""
    try:
        payload: dict[str, str] = {"type": event_type, "actor_sub": actor_sub}
        if calendar_id is not None:
            payload["calendar_id"] = str(calendar_id)
        if event_id is not None:
            payload["event_id"] = str(event_id)
        await get_calendar_manager().publish(CALENDAR_ROOM_ID, payload)
    except Exception:
        logger.exception(
            "Не удалось опубликовать событие календаря: %s calendar_id=%s event_id=%s",
            event_type,
            calendar_id,
            event_id,
        )
