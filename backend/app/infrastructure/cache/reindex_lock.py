"""Распределённая блокировка bulk-переиндексации семантического поиска."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable
from typing import cast

from app.core.config import get_settings
from app.infrastructure.cache.token_cache import get_redis_client

logger = logging.getLogger(__name__)

_REINDEX_LOCK_KEY = "portal:search:reindex:lock"
# Снимать lock только если значение всё ещё наш token
# (иначе чужой job после истечения TTL).
_RELEASE_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
end
return 0
"""
_DEV_LOCK_TOKEN = "local-dev"


async def try_acquire_reindex_lock() -> str | None:
    """Захватить lock (SET NX).

    Token — lock получен, None — переиндексация уже идёт.

    Без Redis — dev-token (fail-open для local / pytest).
    """
    redis = get_redis_client()
    if redis is None:
        return _DEV_LOCK_TOKEN
    ttl = get_settings().reindex_lock_ttl_seconds
    token = str(uuid.uuid4())
    acquired = await redis.set(_REINDEX_LOCK_KEY, token, nx=True, ex=ttl)
    if not acquired:
        return None
    return token


async def release_reindex_lock(token: str) -> None:
    """Снять lock, только если он всё ещё принадлежит ``token``."""
    redis = get_redis_client()
    if redis is None:
        return
    await cast(Awaitable[object], redis.eval(_RELEASE_LOCK_LUA, 1, _REINDEX_LOCK_KEY, token))
    logger.debug("reindex_lock: попытка снять lock token=%s…", token[:8])
