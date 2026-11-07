"""Поведение token_cache при наличии/отсутствии Redis."""

from __future__ import annotations

import hashlib
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.infrastructure.cache import token_cache as tc


def _expected_key(token: str) -> str:
    return f"sso_token:{hashlib.sha256(token.encode()).hexdigest()}"


@pytest.fixture(autouse=True)
def reset_redis_client() -> None:
    tc.set_redis_client(None)
    yield
    tc.set_redis_client(None)


@pytest.mark.asyncio
async def test_get_cached_none_without_client() -> None:
    assert await tc.get_cached_userinfo("t") is None


@pytest.mark.asyncio
async def test_set_cached_noop_without_client() -> None:
    await tc.set_cached_userinfo("t", {"sub": "a"}, 60)
    assert await tc.get_cached_userinfo("t") is None


@pytest.mark.asyncio
async def test_invalidate_noop_without_client() -> None:
    await tc.invalidate_token("t")
    assert await tc.get_cached_userinfo("t") is None


@pytest.mark.asyncio
async def test_get_set_roundtrip_with_mock_redis() -> None:
    store: dict[str, str] = {}

    async def mock_get(key: str) -> str | None:
        return store.get(key)

    async def mock_set(key: str, value: str, ex: int | None = None) -> bool:
        store[key] = value
        return True

    client = MagicMock()
    client.get = AsyncMock(side_effect=mock_get)
    client.set = AsyncMock(side_effect=mock_set)
    tc.set_redis_client(client)

    assert await tc.get_cached_userinfo("abc") is None

    payload = {"sub": "u1", "email": "e@x"}
    await tc.set_cached_userinfo("abc", payload, ttl=120)
    out = await tc.get_cached_userinfo("abc")
    assert out == payload
    client.set.assert_awaited_once()
    assert client.set.await_args.args[0] == _expected_key("abc")
    assert client.set.await_args.kwargs["ex"] == 120


@pytest.mark.asyncio
async def test_get_cached_returns_json_from_redis() -> None:
    key_used: list[str] = []

    async def mock_get(key: str) -> str:
        key_used.append(key)
        return json.dumps({"sub": "x"})

    client = MagicMock()
    client.get = AsyncMock(side_effect=mock_get)
    tc.set_redis_client(client)
    assert (await tc.get_cached_userinfo("tok")) == {"sub": "x"}
    assert key_used[0] == _expected_key("tok")
    assert "tok" not in key_used[0][len("sso_token:") :]


@pytest.mark.asyncio
async def test_get_cached_returns_none_on_broken_json() -> None:
    client = MagicMock()
    client.get = AsyncMock(return_value="not-json{")
    tc.set_redis_client(client)
    assert await tc.get_cached_userinfo("t") is None


@pytest.mark.asyncio
async def test_get_cached_handles_redis_error() -> None:
    client = MagicMock()
    client.get = AsyncMock(side_effect=RuntimeError("down"))
    tc.set_redis_client(client)
    assert await tc.get_cached_userinfo("t") is None


@pytest.mark.asyncio
async def test_set_cached_handles_redis_error() -> None:
    client = MagicMock()
    client.set = AsyncMock(side_effect=RuntimeError("down"))
    client.get = AsyncMock(return_value=None)
    tc.set_redis_client(client)
    await tc.set_cached_userinfo("t", {"sub": "a"}, 1)
    assert await tc.get_cached_userinfo("t") is None


@pytest.mark.asyncio
async def test_invalidate_deletes_key() -> None:
    client = MagicMock()
    client.delete = AsyncMock(return_value=1)
    tc.set_redis_client(client)
    await tc.invalidate_token("tok")
    client.delete.assert_awaited_once_with(_expected_key("tok"))


@pytest.mark.asyncio
async def test_invalidate_handles_redis_error() -> None:
    client = MagicMock()
    client.delete = AsyncMock(side_effect=RuntimeError("down"))
    tc.set_redis_client(client)
    await tc.invalidate_token("t")
    client.delete.assert_awaited_once()
