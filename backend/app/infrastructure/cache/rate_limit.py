"""Скользящее окно rate limit через Redis sorted set (общий слой для middleware и роутеров)."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import uuid
from collections import defaultdict

from starlette.requests import Request

from app.core.exceptions import RateLimitError
from app.infrastructure.cache.token_cache import get_redis_client

logger = logging.getLogger(__name__)

_memory_windows: dict[str, list[float]] = defaultdict(list)
_memory_lock = asyncio.Lock()
# Жёсткий потолок ключей: уникальные IP/токены при недоступном Redis не должны
# раздувать память воркера. Выселяем самые старые окна (по последнему hit).
_MEMORY_WINDOWS_MAX_KEYS = 4096


def rate_limit_client_key(request: Request) -> str:
    """Ключ клиента для rate limit: хэш Bearer-токена или IP."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
        if token:
            digest = hashlib.sha256(token.encode()).hexdigest()[:32]
            return f"tok:{digest}"
    ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


def _evict_memory_windows() -> None:
    """Удалить пустые окна и уложиться в ``_MEMORY_WINDOWS_MAX_KEYS``."""
    empty_keys = [k for k, hits in _memory_windows.items() if not hits]
    for key in empty_keys:
        del _memory_windows[key]
    overflow = len(_memory_windows) - _MEMORY_WINDOWS_MAX_KEYS
    if overflow <= 0:
        return
    oldest_first = sorted(
        _memory_windows.items(),
        key=lambda item: item[1][-1] if item[1] else 0.0,
    )
    for key, _hits in oldest_first[:overflow]:
        del _memory_windows[key]


async def memory_rate_check(key: str, limit: int, window_seconds: int) -> bool:
    """In-process sliding window при недоступном Redis (один воркер)."""
    async with _memory_lock:
        now = time.time()
        window_start = now - window_seconds
        hits = _memory_windows[key]
        hits[:] = [t for t in hits if t > window_start]
        if len(hits) >= limit:
            _evict_memory_windows()
            return False
        hits.append(now)
        _evict_memory_windows()
        return True


async def rate_limit_check(
    key: str,
    limit: int,
    window_seconds: int,
    *,
    redis_client: object | None = None,
) -> bool:
    """True → пропустить запрос, False → превышен лимит.

    Redis — основной store; при ошибке или отсутствии клиента — in-memory fallback.
    """
    redis = redis_client if redis_client is not None else get_redis_client()
    if redis is not None:
        try:
            import redis.asyncio as aioredis  # noqa: PLC0415

            r: aioredis.Redis = redis  # type: ignore[assignment]
            now = time.time()
            window_start = now - window_seconds
            # Уникальный member: одинаковый time.time() иначе схлопывает hit в ZSET
            member = f"{now}:{uuid.uuid4().hex}"

            pipe = r.pipeline()
            pipe.zremrangebyscore(key, "-inf", window_start)
            pipe.zadd(key, {member: now})
            pipe.zcard(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()
            count: int = results[2]
            return count <= limit
        except Exception as exc:
            logger.warning("rate_limit: Redis недоступен, in-memory fallback: %s", exc)

    return await memory_rate_check(key, limit, window_seconds)


async def redis_rate_check(
    redis_client: object,
    key: str,
    limit: int,
    window_seconds: int,
) -> bool:
    """True → пропустить запрос, False → превышен лимит."""
    return await rate_limit_check(key, limit, window_seconds, redis_client=redis_client)


async def enforce_rate_limit(
    key: str,
    *,
    limit: int,
    window_seconds: int,
    message: str = "Слишком много запросов. Попробуйте позже.",
) -> None:
    """Проверить лимит; при превышении — ``RateLimitError`` (429)."""
    allowed = await rate_limit_check(key, limit, window_seconds)
    if not allowed:
        logger.warning("rate_limit: превышен лимит %d/%ds key=%s", limit, window_seconds, key)
        raise RateLimitError(message)
