from __future__ import annotations

from datetime import timedelta

from sqlalchemy import or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import now_utc
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile

# Не чаще одного обновления last_seen_at при видимой вкладке (~100 пользователей — нагрузка всё равно мала)
_LAST_SEEN_THROTTLE_SEC = 30


async def touch_last_seen_in_db(session: AsyncSession, *, user_sub: str, visible: bool) -> None:
    """Фиксирует момент присутствия в профиле при видимой вкладке.

    При ``visible=False`` — no-op (скрытая вкладка не должна обновлять «был в сети»).
    При ``visible=True`` — обновляем не чаще, чем раз в :data:`_LAST_SEEN_THROTTLE_SEC` секунд.
    Для однократной фиксации ухода — :func:`finalize_last_seen_in_db`.
    """
    if not visible:
        return

    now = now_utc()
    threshold = now - timedelta(seconds=_LAST_SEEN_THROTTLE_SEC)
    await session.execute(
        update(PortalUserProfile)
        .where(PortalUserProfile.sub == user_sub)
        .where(
            or_(
                PortalUserProfile.last_seen_at.is_(None),
                PortalUserProfile.last_seen_at < threshold,
            ),
        )
        .values(last_seen_at=now),
    )
    await session.commit()


async def finalize_last_seen_in_db(session: AsyncSession, *, user_sub: str) -> None:
    """Однократно записывает «ушёл сейчас» (pagehide-beacon, закрытие вкладки)."""
    now = now_utc()
    await session.execute(
        update(PortalUserProfile).where(PortalUserProfile.sub == user_sub).values(last_seen_at=now),
    )
    await session.commit()
