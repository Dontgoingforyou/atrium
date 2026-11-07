"""Кэш meta фото EA в Redis (version / has_photo). Без Redis — no-op."""

from __future__ import annotations

import json
import logging

from app.core.config import get_settings
from app.infrastructure.cache.token_cache import get_redis_client
from app.integrations.effective_admin.client import PhotoMeta

logger = logging.getLogger(__name__)


def _key(username: str) -> str:
    return f"ea_photo_meta:{username.lower()}"


async def get_cached_photo_meta(username: str) -> PhotoMeta | None:
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = await client.get(_key(username))
        if raw is None:
            return None
        data = json.loads(raw)
        return PhotoMeta(has_photo=bool(data.get("has_photo")), version=data.get("version"))
    except Exception as exc:
        logger.warning("Redis photo meta get: %s", exc)
        return None


async def get_cached_photo_meta_bulk(usernames: list[str]) -> dict[str, PhotoMeta | None]:
    """Батч GET meta по username; отсутствующие ключи — ``None``."""
    out: dict[str, PhotoMeta | None] = {u: None for u in usernames}
    client = get_redis_client()
    if client is None or not usernames:
        return out
    try:
        pipe = client.pipeline()
        for uname in usernames:
            pipe.get(_key(uname))
        rows = await pipe.execute()
    except Exception as exc:
        logger.warning("Redis photo meta mget: %s", exc)
        return out
    for uname, raw in zip(usernames, rows, strict=True):
        if raw is None:
            continue
        try:
            data = json.loads(raw)
            out[uname] = PhotoMeta(has_photo=bool(data.get("has_photo")), version=data.get("version"))
        except Exception:
            continue
    return out


async def set_cached_photo_meta(username: str, meta: PhotoMeta) -> None:
    client = get_redis_client()
    if client is None:
        return
    ttl = get_settings().user_photo_meta_cache_seconds
    try:
        await client.set(
            _key(username),
            json.dumps({"has_photo": meta.has_photo, "version": meta.version}),
            ex=ttl,
        )
    except Exception as exc:
        logger.warning("Redis photo meta set: %s", exc)
