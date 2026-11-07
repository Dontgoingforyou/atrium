"""Присутствие пользователей (Redis): онлайн / отошёл / не в сети."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable
from datetime import datetime
from typing import Any, cast

from app.core.enums import PresenceState
from app.core.utils import now_utc
from app.infrastructure.cache.token_cache import get_redis_client

logger = logging.getLogger(__name__)

# Нет heartbeat дольше — считаем пользователя не в сети.
# 30 с — fallback на случай, если pagehide-beacon или inbox WS disconnect не сработали.
_OFFLINE_AFTER_NO_HEARTBEAT_SEC = 30
# Активность не позже этого порога (сек) — «онлайн», иначе при живом heartbeat — «отошёл»
_ACTIVE_ONLINE_MAX_SEC = 180

_KEY_PREFIX = "portal:presence:"
_TTL_SEC = 300

# Отдельный ключ для «когда последний раз видели» — живёт дольше, не удаляется при оффлайн.
# Фронт читает через /portal/users/presence каждые 12 с без лишних SQL-запросов.
_LAST_SEEN_ISO_PREFIX = "portal:last_seen_iso:"
_LAST_SEEN_ISO_TTL_SEC = 7 * 24 * 3600  # 7 дней


def _key(sub: str) -> str:
    return f"{_KEY_PREFIX}{sub}"


def _iso_key(sub: str) -> str:
    return f"{_LAST_SEEN_ISO_PREFIX}{sub}"


def _now_iso() -> str:
    return now_utc().isoformat()


async def set_last_seen_iso_now(*, user_sub: str) -> None:
    """Фиксирует ISO last seen в Redis (beacon / уход с вкладки)."""
    r = get_redis_client()
    if r is None:
        return
    iso_k = _iso_key(user_sub)
    try:
        await cast(
            Awaitable[Any],
            r.set(iso_k, _now_iso(), ex=_LAST_SEEN_ISO_TTL_SEC),
        )
    except Exception as exc:
        logger.warning("Redis last_seen_iso write error: %s", exc)


async def record_presence(*, user_sub: str, visible: bool, active: bool) -> None:
    """Обновляет метки присутствия. При ``visible=False`` ключ удаляется (офлайн для списка);
    ``last_seen_iso`` не трогаем — иначе фоновый heartbeat сбрасывает «был(а) только что»."""
    r = get_redis_client()
    if r is None:
        return
    key = _key(user_sub)
    iso_k = _iso_key(user_sub)
    now_iso = _now_iso()
    try:
        if not visible:
            await cast(Awaitable[Any], r.delete(key))
            return
        now = int(time.time())
        if active:
            await cast(Awaitable[Any], r.hset(key, mapping={"last_seen": str(now), "last_active": str(now)}))
        else:
            prev_la = await cast(Awaitable[str | None], r.hget(key, "last_active"))
            last_active = int(prev_la) if prev_la is not None else now
            await cast(
                Awaitable[Any],
                r.hset(key, mapping={"last_seen": str(now), "last_active": str(last_active)}),
            )
        await cast(Awaitable[Any], r.expire(key, _TTL_SEC))
        await cast(Awaitable[Any], r.set(iso_k, now_iso, ex=_LAST_SEEN_ISO_TTL_SEC))
    except Exception as exc:
        logger.warning("Redis presence write error: %s", exc)


def _status_from_hash(data: dict[str, str], now: int) -> PresenceState:
    if not data:
        return "offline"
    try:
        last_seen = int(data.get("last_seen", "0"))
        last_active = int(data.get("last_active", "0"))
    except ValueError:
        return "offline"
    if last_seen <= 0 or now - last_seen > _OFFLINE_AFTER_NO_HEARTBEAT_SEC:
        return "offline"
    if now - last_active <= _ACTIVE_ONLINE_MAX_SEC:
        return "online"
    return "away"


async def presence_for_subs(subs: list[str]) -> dict[str, PresenceState]:
    """Возвращает статус для каждого sub (по умолчанию offline при отсутствии Redis/данных)."""
    r = get_redis_client()
    now = int(time.time())
    out: dict[str, PresenceState] = {s: "offline" for s in subs}
    if r is None or not subs:
        return out
    try:
        pipe = r.pipeline()
        for s in subs:
            pipe.hgetall(_key(s))
        rows = await cast(Awaitable[list[Any]], pipe.execute())
    except Exception as exc:
        logger.warning("Redis presence read error: %s", exc)
        return out
    for sub, raw in zip(subs, rows, strict=True):
        m = dict(raw) if isinstance(raw, dict) else {}
        out[sub] = _status_from_hash(m, now)
    return out


async def bulk_last_seen_iso(subs: list[str]) -> dict[str, datetime | None]:
    """Возвращает ``last_seen_at`` из Redis (отдельный долгоживущий ключ) без SQL-запросов.

    Ключ обновляется при heartbeat с видимой вкладкой и при :func:`set_last_seen_iso_now` (beacon).
    """
    r = get_redis_client()
    out: dict[str, datetime | None] = {s: None for s in subs}
    if r is None or not subs:
        return out
    try:
        pipe = r.pipeline()
        for s in subs:
            pipe.get(_iso_key(s))
        rows = await cast(Awaitable[list[Any]], pipe.execute())
    except Exception as exc:
        logger.warning("Redis last_seen_iso read error: %s", exc)
        return out
    for sub, val in zip(subs, rows, strict=True):
        if isinstance(val, (str, bytes)):
            raw = val.decode() if isinstance(val, bytes) else val
            try:
                out[sub] = datetime.fromisoformat(raw)
            except ValueError:
                pass
    return out
