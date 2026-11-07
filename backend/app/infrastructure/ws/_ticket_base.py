"""Общая инфраструктура одноразовых WS-тикетов: хранилище и базовые операции."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

TICKET_TTL_SEC = 30

# Резерв при отсутствии Redis (тесты / dev): не шарится между воркерами
_mem_store: dict[str, tuple[str, float]] = {}
_mem_lock = asyncio.Lock()


async def _store_ticket(
    redis: aioredis.Redis | None,
    full_key: str,
    payload_dict: dict,  # type: ignore[type-arg]
) -> str:
    """Сохранить тикет в Redis или in-memory; вернуть сгенерированный ticket_id."""
    ticket_id = str(uuid.uuid4())
    keyed = f"{full_key}{ticket_id}"
    payload = json.dumps(payload_dict)
    if redis is not None:
        await redis.set(keyed, payload, ex=TICKET_TTL_SEC)
    else:
        async with _mem_lock:
            _mem_store[keyed] = (payload, time.monotonic() + TICKET_TTL_SEC)
    return ticket_id


async def _retrieve_ticket(redis: aioredis.Redis | None, keyed: str) -> str | None:
    """Атомарно прочитать и удалить тикет; вернуть сырой JSON или None."""
    raw: str | None = None
    if redis is not None:
        raw_val = await redis.getdel(keyed)
        raw = raw_val.decode() if isinstance(raw_val, bytes) else raw_val
    else:
        async with _mem_lock:
            now = time.monotonic()
            for k, (_, exp) in list(_mem_store.items()):
                if exp < now:
                    _mem_store.pop(k, None)
            entry = _mem_store.pop(keyed, None)
            if entry is not None:
                pl, exp = entry
                if exp >= now:
                    raw = pl
    return raw
