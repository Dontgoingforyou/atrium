"""Кэш SSO-токенов в Redis.

Принцип работы:
- Ключ: sha256(raw_token) → строка вида ``sso_token:{hex}``
- Значение: JSON с payload userinfo (sub, email, groups, …)
- TTL: ``Settings.token_cache_ttl`` (по умолчанию 300 сек / 5 мин)

Threat model: кэш хранит userinfo после успешного вызова SSO; подпись JWT
на API не проверяется (доверяем шлюзу). Смена групп в IdP действует с задержкой
до истечения TTL. Инвалидация — ``invalidate_token`` при logout.

Если Redis не настроен (REDIS_URL пустой) или недоступен — все функции
работают как no-op/None, основная логика валидации проходит напрямую через SSO.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_redis_client: aioredis.Redis | None = None


def set_redis_client(client: aioredis.Redis | None) -> None:
    global _redis_client
    _redis_client = client


def get_redis_client() -> aioredis.Redis | None:
    return _redis_client


def _token_key(token: str) -> str:
    digest = hashlib.sha256(token.encode()).hexdigest()
    return f"sso_token:{digest}"


async def get_cached_userinfo(token: str) -> dict[str, Any] | None:
    """Возвращает закэшированный payload или None."""
    client = _redis_client
    if client is None:
        return None
    try:
        raw = await client.get(_token_key(token))
        if raw is None:
            return None
        return json.loads(raw)  # type: ignore[no-any-return]
    except Exception as exc:
        logger.warning("Redis get error: %s", exc)
        return None


async def set_cached_userinfo(token: str, userinfo: dict[str, Any], ttl: int) -> None:
    """Кэширует payload на ttl секунд."""
    client = _redis_client
    if client is None:
        return
    try:
        await client.set(_token_key(token), json.dumps(userinfo), ex=ttl)
    except Exception as exc:
        logger.warning("Redis set error: %s", exc)


async def invalidate_token(token: str) -> None:
    """Явно инвалидирует кэш токена (напр. при logout)."""
    client = _redis_client
    if client is None:
        return
    try:
        await client.delete(_token_key(token))
    except Exception as exc:
        logger.warning("Redis delete error: %s", exc)
