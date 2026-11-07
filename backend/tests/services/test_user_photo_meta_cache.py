"""Батч-чтение meta фото EA из Redis (pipeline, без N+1 GET)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.config import Settings
from app.infrastructure.cache import token_cache as tc
from app.integrations.effective_admin.client import PhotoMeta
from app.services import user_photo_meta_cache as pmc


@pytest.fixture(autouse=True)
def reset_redis_client() -> None:
    tc.set_redis_client(None)
    yield
    tc.set_redis_client(None)


@pytest.mark.asyncio
async def test_get_cached_photo_meta_bulk_without_client() -> None:
    out = await pmc.get_cached_photo_meta_bulk(["alice", "bob"])
    assert out == {"alice": None, "bob": None}


@pytest.mark.asyncio
async def test_get_cached_photo_meta_bulk_pipeline() -> None:
    pipe = MagicMock()
    pipe.get = MagicMock()
    pipe.execute = AsyncMock(
        return_value=[
            json.dumps({"has_photo": True, "version": "v1"}),
            None,
        ]
    )
    client = MagicMock()
    client.pipeline = MagicMock(return_value=pipe)
    tc.set_redis_client(client)

    out = await pmc.get_cached_photo_meta_bulk(["alice", "bob"])
    assert out["alice"] is not None
    assert out["alice"].has_photo is True
    assert out["alice"].version == "v1"
    assert out["bob"] is None
    assert pipe.get.call_count == 2


@pytest.mark.asyncio
async def test_get_cached_photo_meta_single_hit() -> None:
    client = MagicMock()
    client.get = AsyncMock(return_value=json.dumps({"has_photo": True, "version": 7}))
    tc.set_redis_client(client)

    meta = await pmc.get_cached_photo_meta("Alice")
    assert meta is not None
    assert meta.has_photo is True
    assert meta.version == 7
    client.get.assert_awaited_once_with("ea_photo_meta:alice")


@pytest.mark.asyncio
async def test_get_cached_photo_meta_malformed_json_returns_none() -> None:
    client = MagicMock()
    client.get = AsyncMock(return_value="{not-json")
    tc.set_redis_client(client)

    assert await pmc.get_cached_photo_meta("bob") is None


@pytest.mark.asyncio
async def test_get_cached_photo_meta_redis_error_returns_none() -> None:
    client = MagicMock()
    client.get = AsyncMock(side_effect=RuntimeError("redis down"))
    tc.set_redis_client(client)

    assert await pmc.get_cached_photo_meta("bob") is None


@pytest.mark.asyncio
async def test_set_cached_photo_meta_writes_with_ttl() -> None:
    client = MagicMock()
    client.set = AsyncMock()
    tc.set_redis_client(client)
    settings = Settings(
        database_url="sqlite:///:memory:",
        user_photo_meta_cache_seconds=123,
    )
    meta = PhotoMeta(has_photo=True, version=5)

    with patch("app.services.user_photo_meta_cache.get_settings", return_value=settings):
        await pmc.set_cached_photo_meta("User.Name", meta)

    client.set.assert_awaited_once()
    key, payload = client.set.await_args.args[0], client.set.await_args.args[1]
    assert key == "ea_photo_meta:user.name"
    assert json.loads(payload) == {"has_photo": True, "version": 5}
    assert client.set.await_args.kwargs["ex"] == 123


@pytest.mark.asyncio
async def test_get_cached_photo_meta_bulk_malformed_row_skipped() -> None:
    pipe = MagicMock()
    pipe.get = MagicMock()
    pipe.execute = AsyncMock(return_value=["{bad"])
    client = MagicMock()
    client.pipeline = MagicMock(return_value=pipe)
    tc.set_redis_client(client)

    out = await pmc.get_cached_photo_meta_bulk(["x"])
    assert out["x"] is None
