from __future__ import annotations

import logging
from typing import Any

from app.infrastructure.ws.room_manager import SPECIALIST_BOARD_ROOM_ID

logger = logging.getLogger(__name__)


async def publish_specialist_board_event(
    event_type: str,
    *,
    specialist_sub: str | None = None,
    manager_sub: str | None = None,
    actor_sub: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Событие в глобальную комнату доски (менеджеры и администраторы с активным WS)."""
    payload: dict[str, Any] = {"type": event_type}
    if specialist_sub is not None:
        payload["specialist_sub"] = specialist_sub
    if manager_sub is not None:
        payload["manager_sub"] = manager_sub
    if actor_sub is not None:
        payload["actor_sub"] = actor_sub
    if extra:
        payload.update(extra)
    try:
        from app.infrastructure.ws.managers import get_specialist_board_manager

        await get_specialist_board_manager().publish(SPECIALIST_BOARD_ROOM_ID, payload)
    except Exception:
        logger.warning(
            "Не удалось опубликовать событие доски специалистов: %s specialist_sub=%s",
            event_type,
            specialist_sub,
        )
