"""Кэш результата emails/check в Redis. Без Redis — no-op."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.infrastructure.cache.token_cache import get_redis_client

logger = logging.getLogger(__name__)

_ACTIVE = "1"
_INACTIVE = "0"


def _key(email: str) -> str:
    return f"ea_email_active:{email.lower()}"


async def get_cached_email_active_bulk(emails: list[str]) -> dict[str, bool | None]:
    """Батч GET: ``True`` — активен, ``False`` — нет в каталоге, ``None`` — промах."""
    out: dict[str, bool | None] = {email: None for email in emails}
    client = get_redis_client()
    if client is None or not emails:
        return out
    try:
        pipe = client.pipeline()
        for email in emails:
            pipe.get(_key(email))
        rows = await pipe.execute()
    except Exception as exc:
        logger.warning("Redis email-active mget: %s", exc)
        return out
    for email, raw in zip(emails, rows, strict=True):
        if raw is None:
            continue
        value = raw.decode() if isinstance(raw, bytes) else str(raw)
        if value == _ACTIVE:
            out[email] = True
        elif value == _INACTIVE:
            out[email] = False
    return out


async def set_cached_email_active_bulk(active_by_email: dict[str, bool]) -> None:
    client = get_redis_client()
    if client is None or not active_by_email:
        return
    ttl = get_settings().user_photo_meta_cache_seconds
    try:
        pipe = client.pipeline()
        for email, active in active_by_email.items():
            pipe.set(_key(email), _ACTIVE if active else _INACTIVE, ex=ttl)
        await pipe.execute()
    except Exception as exc:
        logger.warning("Redis email-active mset: %s", exc)
