"""Тесты rate limit и reindex lock."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.exceptions import RateLimitError
from app.infrastructure.cache.rate_limit import (
    _memory_windows,
    enforce_rate_limit,
    memory_rate_check,
    rate_limit_check,
    rate_limit_client_key,
)
from app.infrastructure.cache.reindex_lock import release_reindex_lock, try_acquire_reindex_lock
from app.middleware.rate_limit import ApiRateLimitMiddleware
from starlette.requests import Request


def _asgi_status_and_body(responses: list[dict]) -> tuple[int, dict[str, object]]:
    start = next(m for m in responses if m.get("type") == "http.response.start")
    body = b"".join(m.get("body", b"") for m in responses if m.get("type") == "http.response.body")
    return int(start["status"]), json.loads(body)


def test_rate_limit_client_key_uses_token_hash() -> None:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"authorization", b"Bearer secret-token")],
        "query_string": b"",
    }
    key = rate_limit_client_key(Request(scope))
    assert key.startswith("tok:")
    assert key != "tok:secret-token"


def test_rate_limit_client_key_falls_back_to_ip() -> None:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "client": ("10.0.0.5", 12345),
    }
    assert rate_limit_client_key(Request(scope)) == "ip:10.0.0.5"


def test_rate_limit_client_key_empty_bearer_uses_ip() -> None:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"authorization", b"Bearer ")],
        "query_string": b"",
        "client": ("10.0.0.5", 12345),
    }
    assert rate_limit_client_key(Request(scope)) == "ip:10.0.0.5"


def test_rate_limit_client_key_unknown_without_client() -> None:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
    }
    assert rate_limit_client_key(Request(scope)) == "ip:unknown"


async def test_api_rate_limit_blocks_health_flood() -> None:
    app_mock = AsyncMock()
    middleware = ApiRateLimitMiddleware(app_mock)
    responses: list[dict] = []

    async def capture_send(msg: dict) -> None:
        responses.append(msg)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/health",
        "query_string": b"",
        "headers": [],
        "client": ("1.2.3.4", 12345),
    }

    with (
        patch("app.middleware.rate_limit.rate_limit_check", new=AsyncMock(return_value=False)),
        patch("app.infrastructure.cache.token_cache.get_redis_client", return_value=MagicMock()),
    ):
        await middleware(scope, AsyncMock(), capture_send)

    app_mock.assert_not_called()
    status, payload = _asgi_status_and_body(responses)
    assert status == 429
    assert payload.get("code") == "rate_limited"


async def test_api_rate_limit_blocks_bench_export_flood() -> None:
    """GET бенча лимитируется по IP, не по уникальному Bearer."""
    app_mock = AsyncMock()
    middleware = ApiRateLimitMiddleware(app_mock)
    responses: list[dict] = []

    async def capture_send(msg: dict) -> None:
        responses.append(msg)

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v1/integrations/bench",
        "query_string": b"",
        "headers": [(b"authorization", b"Bearer unique-token-aaa")],
        "client": ("1.2.3.4", 12345),
    }

    with (
        patch("app.middleware.rate_limit.rate_limit_check", new=AsyncMock(return_value=False)),
        patch("app.infrastructure.cache.token_cache.get_redis_client", return_value=MagicMock()),
    ):
        await middleware(scope, AsyncMock(), capture_send)

    app_mock.assert_not_called()
    status, payload = _asgi_status_and_body(responses)
    assert status == 429
    assert payload.get("code") == "rate_limited"


async def test_api_rate_limit_ip_ceiling_blocks_unique_bearers() -> None:
    """Случайный Bearer не должен давать бесконечные вёдра: срабатывает потолок IP."""
    app_mock = AsyncMock()
    middleware = ApiRateLimitMiddleware(app_mock)
    responses: list[dict] = []

    async def capture_send(msg: dict) -> None:
        responses.append(msg)

    async def check(key: str, limit: int, window_seconds: int, **_kwargs: object) -> bool:
        if key.startswith("rl:api-mut-ip:"):
            return False
        return True

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/portal/chats",
        "query_string": b"",
        "headers": [(b"authorization", b"Bearer unique-token-aaa")],
        "client": ("1.2.3.4", 12345),
    }

    with patch("app.middleware.rate_limit.rate_limit_check", new=AsyncMock(side_effect=check)):
        await middleware(scope, AsyncMock(), capture_send)

    app_mock.assert_not_called()
    status, payload = _asgi_status_and_body(responses)
    assert status == 429
    assert payload.get("code") == "rate_limited"


async def test_api_rate_limit_skips_auth_paths() -> None:
    app_mock = AsyncMock()
    middleware = ApiRateLimitMiddleware(app_mock)
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/token",
        "query_string": b"",
        "headers": [],
        "client": ("1.2.3.4", 12345),
    }

    with (
        patch("app.middleware.rate_limit.rate_limit_check", new=AsyncMock(return_value=False)) as chk,
        patch("app.infrastructure.cache.token_cache.get_redis_client", return_value=MagicMock()),
    ):
        await middleware(scope, AsyncMock(), AsyncMock())

    chk.assert_not_called()
    app_mock.assert_called_once()


async def test_enforce_rate_limit_raises_when_exceeded() -> None:
    redis = MagicMock()
    with (
        patch("app.infrastructure.cache.rate_limit.get_redis_client", return_value=redis),
        patch("app.infrastructure.cache.rate_limit.rate_limit_check", new=AsyncMock(return_value=False)),
    ):
        with pytest.raises(RateLimitError):
            await enforce_rate_limit("rl:test", limit=5, window_seconds=60)


async def test_enforce_rate_limit_memory_fallback_without_redis() -> None:
    key = "rl:enforce-mem"
    _memory_windows.pop(key, None)
    try:
        with patch("app.infrastructure.cache.rate_limit.get_redis_client", return_value=None):
            await enforce_rate_limit(key, limit=1, window_seconds=60)
            with pytest.raises(RateLimitError):
                await enforce_rate_limit(key, limit=1, window_seconds=60)
    finally:
        _memory_windows.pop(key, None)


async def test_rate_limit_check_unique_zset_members_on_same_timestamp() -> None:
    members: list[str] = []
    pipe = MagicMock()
    pipe.zremrangebyscore = MagicMock(return_value=pipe)
    pipe.zcard = MagicMock(return_value=pipe)
    pipe.expire = MagicMock(return_value=pipe)

    def _zadd(_key: str, mapping: dict[str, float]) -> MagicMock:
        members.extend(mapping.keys())
        return pipe

    pipe.zadd = _zadd
    pipe.execute = AsyncMock(return_value=[0, 1, 1, True])
    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=pipe)

    with patch("app.infrastructure.cache.rate_limit.time.time", return_value=1_700_000_000.0):
        assert await rate_limit_check("rl:k", 10, 60, redis_client=redis)
        assert await rate_limit_check("rl:k", 10, 60, redis_client=redis)

    assert len(members) == 2
    assert members[0] != members[1]


async def test_memory_rate_check_blocks_at_limit() -> None:
    """In-memory fallback — не fail-open: после лимита следующие запросы режутся."""
    key = "rl:mem-block"
    _memory_windows.pop(key, None)
    try:
        assert await memory_rate_check(key, limit=2, window_seconds=60) is True
        assert await memory_rate_check(key, limit=2, window_seconds=60) is True
        assert await memory_rate_check(key, limit=2, window_seconds=60) is False
    finally:
        _memory_windows.pop(key, None)


async def test_memory_rate_check_prunes_hits_outside_window() -> None:
    key = "rl:mem-window"
    _memory_windows.pop(key, None)
    try:
        with patch("app.infrastructure.cache.rate_limit.time.time", return_value=1000.0):
            assert await memory_rate_check(key, limit=1, window_seconds=10) is True
            assert await memory_rate_check(key, limit=1, window_seconds=10) is False
        with patch("app.infrastructure.cache.rate_limit.time.time", return_value=1020.0):
            assert await memory_rate_check(key, limit=1, window_seconds=10) is True
    finally:
        _memory_windows.pop(key, None)


async def test_memory_windows_evict_oldest_when_over_cap() -> None:
    _memory_windows.clear()
    try:
        with patch("app.infrastructure.cache.rate_limit._MEMORY_WINDOWS_MAX_KEYS", 8):
            for i in range(12):
                assert await memory_rate_check(f"rl:cap:{i}", limit=10, window_seconds=60) is True
        assert len(_memory_windows) == 8
        assert "rl:cap:0" not in _memory_windows
        assert "rl:cap:11" in _memory_windows
    finally:
        _memory_windows.clear()


async def test_try_acquire_reindex_lock_without_redis() -> None:
    with patch("app.infrastructure.cache.reindex_lock.get_redis_client", return_value=None):
        token = await try_acquire_reindex_lock()
        assert token == "local-dev"


async def test_release_reindex_lock_noop_without_redis() -> None:
    with patch("app.infrastructure.cache.reindex_lock.get_redis_client", return_value=None):
        await release_reindex_lock("tok-owner")


async def test_try_acquire_reindex_lock_set_nx() -> None:
    redis = MagicMock()
    redis.set = AsyncMock(return_value=True)
    with (
        patch("app.infrastructure.cache.reindex_lock.get_redis_client", return_value=redis),
        patch("app.infrastructure.cache.reindex_lock.get_settings") as gs,
    ):
        gs.return_value.reindex_lock_ttl_seconds = 3600
        token = await try_acquire_reindex_lock()
        assert token is not None
        redis.set.assert_awaited_once()
        assert redis.set.await_args.args[1] == token


async def test_try_acquire_reindex_lock_busy() -> None:
    redis = MagicMock()
    redis.set = AsyncMock(return_value=False)
    with patch("app.infrastructure.cache.reindex_lock.get_redis_client", return_value=redis):
        assert await try_acquire_reindex_lock() is None


async def test_release_reindex_lock_uses_fencing_token() -> None:
    redis = MagicMock()
    redis.eval = AsyncMock()
    with patch("app.infrastructure.cache.reindex_lock.get_redis_client", return_value=redis):
        await release_reindex_lock("tok-owner")
        redis.eval.assert_awaited_once()
        assert redis.eval.await_args.args[3] == "tok-owner"
