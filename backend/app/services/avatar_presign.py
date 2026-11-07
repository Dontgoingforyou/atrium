"""Presigned URL для аватаров (профиль пользователя, чат, доска) — единый TTL из Settings."""

from __future__ import annotations

from app.core.config import get_settings
from app.infrastructure.storage.client import async_get_presigned_url, get_presigned_url


def presign_avatar_url(storage_key: str | None, *, ttl_seconds: int | None = None) -> str | None:
    if not storage_key:
        return None
    ttl = ttl_seconds if ttl_seconds is not None else get_settings().avatar_presign_ttl_seconds
    return get_presigned_url(storage_key, ttl_seconds=ttl)


async def async_presign_avatar_url(storage_key: str | None, *, ttl_seconds: int | None = None) -> str | None:
    if not storage_key:
        return None
    ttl = ttl_seconds if ttl_seconds is not None else get_settings().avatar_presign_ttl_seconds
    return await async_get_presigned_url(storage_key, ttl_seconds=ttl)
