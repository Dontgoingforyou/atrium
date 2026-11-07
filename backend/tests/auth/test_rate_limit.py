"""Тесты AuthRateLimitMiddleware и функции redis_rate_check (sliding window)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.infrastructure.cache.rate_limit import redis_rate_check
from app.main import app
from app.middleware.rate_limit import AuthRateLimitMiddleware
from httpx import ASGITransport, AsyncClient

# ---------------------------------------------------------------------------
# redis_rate_check: sliding window через sorted set
# ---------------------------------------------------------------------------


def _make_pipeline(count: int) -> MagicMock:
    """Создать мок pipeline с заданным результатом zcard (индекс 2)."""
    pipe = MagicMock()
    pipe.execute = AsyncMock(return_value=[0, 1, count, 1])
    pipe.zremrangebyscore = MagicMock()
    pipe.zadd = MagicMock()
    pipe.zcard = MagicMock()
    pipe.expire = MagicMock()
    return pipe


def _make_redis(pipe: MagicMock) -> MagicMock:
    redis = MagicMock()
    redis.pipeline = MagicMock(return_value=pipe)
    return redis


async def test_sliding_window_allows_within_limit() -> None:
    """Запрос пропускается, если счётчик в окне не превышает лимит."""
    pipe = _make_pipeline(count=10)
    redis = _make_redis(pipe)

    result = await redis_rate_check(redis, "rl:/api/v1/auth/token:1.2.3.4", limit=20, window_seconds=60)

    assert result is True
    pipe.zremrangebyscore.assert_called_once()
    pipe.zadd.assert_called_once()
    pipe.zcard.assert_called_once()
    pipe.expire.assert_called_once()


async def test_sliding_window_allows_at_exact_limit() -> None:
    """Ровно на пределе — запрос пропускается (count == limit)."""
    pipe = _make_pipeline(count=20)
    redis = _make_redis(pipe)

    result = await redis_rate_check(redis, "rl:/api/v1/auth/token:1.2.3.4", limit=20, window_seconds=60)

    assert result is True


async def test_sliding_window_blocks_over_limit() -> None:
    """Запрос блокируется, когда счётчик превышает лимит."""
    pipe = _make_pipeline(count=21)
    redis = _make_redis(pipe)

    result = await redis_rate_check(redis, "rl:/api/v1/auth/token:1.2.3.4", limit=20, window_seconds=60)

    assert result is False


@pytest.mark.parametrize("count", [100, 9999])
async def test_sliding_window_blocks_far_over_limit(count: int) -> None:
    """Блокировка при значительном превышении лимита."""
    pipe = _make_pipeline(count=count)
    redis = _make_redis(pipe)

    result = await redis_rate_check(redis, "rl:/api/v1/auth/token:1.2.3.4", limit=20, window_seconds=60)

    assert result is False


async def test_memory_fallback_allows_first_request_when_redis_unavailable() -> None:
    """При ошибке Redis — in-memory fallback, первый запрос в пустом окне проходит."""
    redis = MagicMock()
    redis.pipeline = MagicMock(side_effect=Exception("Redis connection refused"))

    result = await redis_rate_check(redis, "rl:/api/v1/auth/token:1.2.3.4", limit=20, window_seconds=60)

    assert result is True


async def test_memory_fallback_when_pipeline_execute_raises() -> None:
    """При ошибке pipeline.execute() — тот же in-memory fallback, не безлимитный fail-open."""
    pipe = MagicMock()
    pipe.execute = AsyncMock(side_effect=ConnectionError("Redis timeout"))
    pipe.zremrangebyscore = MagicMock()
    pipe.zadd = MagicMock()
    pipe.zcard = MagicMock()
    pipe.expire = MagicMock()
    redis = _make_redis(pipe)

    result = await redis_rate_check(redis, "rl:/api/v1/auth/token:1.2.3.4", limit=20, window_seconds=60)

    assert result is True


# ---------------------------------------------------------------------------
# AuthRateLimitMiddleware: пути и ответы
# ---------------------------------------------------------------------------


async def test_middleware_passes_non_limited_path() -> None:
    """Запросы на пути вне лимита проходят без обращения к Redis."""
    app_mock = AsyncMock()
    middleware = AuthRateLimitMiddleware(app_mock)

    scope = {"type": "http", "method": "GET", "path": "/api/v1/auth/me", "query_string": b"", "headers": []}
    receive = AsyncMock()
    send = AsyncMock()

    with patch("app.middleware.rate_limit.rate_limit_check") as rate_check:
        await middleware(scope, receive, send)

    rate_check.assert_not_called()
    app_mock.assert_called_once()


async def test_middleware_passes_websocket_scope() -> None:
    """WS-соединения (type=websocket) не попадают под rate limit."""
    app_mock = AsyncMock()
    middleware = AuthRateLimitMiddleware(app_mock)

    scope = {"type": "websocket", "path": "/ws", "query_string": b"", "headers": []}
    receive = AsyncMock()
    send = AsyncMock()

    with patch("app.middleware.rate_limit.rate_limit_check") as rate_check:
        await middleware(scope, receive, send)

    rate_check.assert_not_called()
    app_mock.assert_called_once()


async def test_middleware_returns_429_when_limit_exceeded() -> None:
    """Middleware отвечает 429 и Retry-After при превышении лимита."""
    app_mock = AsyncMock()
    middleware = AuthRateLimitMiddleware(app_mock)

    responses: list[dict] = []

    async def capture_send(msg: dict) -> None:
        responses.append(msg)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/token",
        "query_string": b"",
        "headers": [],
        "client": ("1.2.3.4", 12345),
    }
    receive = AsyncMock()

    with (
        patch("app.middleware.rate_limit.rate_limit_check", new=AsyncMock(return_value=False)),
        patch("app.infrastructure.cache.token_cache.get_redis_client", return_value=MagicMock()),
    ):
        await middleware(scope, receive, capture_send)

    app_mock.assert_not_called()
    status_messages = [m for m in responses if m.get("type") == "http.response.start"]
    assert status_messages, "Ответ должен содержать http.response.start"
    assert status_messages[0]["status"] == 429
    header_list = status_messages[0].get("headers") or []
    retry_after = next((v.decode() for k, v in header_list if k.lower() == b"retry-after"), None)
    assert retry_after is not None


async def test_rate_limited_response_has_request_id_and_security_headers() -> None:
    """Регрессия на порядок middleware в main.py: RequestId/SecurityHeaders обёрнуты
    снаружи AuthRateLimit/ApiRateLimit, поэтому 429 обязан их получать так же, как и
    любой другой ответ (см. .cursor/rules/logging.mdc, error-handling.mdc)."""
    transport = ASGITransport(app=app)
    with patch("app.middleware.rate_limit.rate_limit_check", new=AsyncMock(return_value=False)):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get(
                "/api/v1/auth/authorization-url",
                headers={"X-Request-ID": "rid-rate-limited"},
            )

    assert r.status_code == 429
    assert r.headers.get("x-request-id") == "rid-rate-limited"
    assert r.json().get("request_id") == "rid-rate-limited"
    assert r.json().get("code") == "rate_limited"
    assert r.headers.get("retry-after")
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("x-frame-options") == "DENY"


async def test_middleware_uses_memory_fallback_when_redis_none() -> None:
    """Если клиент Redis None, middleware использует in-memory fallback и пропускает первый запрос."""
    app_mock = AsyncMock()
    middleware = AuthRateLimitMiddleware(app_mock)

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/token",
        "query_string": b"",
        "headers": [],
        "client": ("1.2.3.4", 12345),
    }
    receive = AsyncMock()
    send = AsyncMock()

    with (
        patch("app.infrastructure.cache.token_cache.get_redis_client", return_value=None),
    ):
        await middleware(scope, receive, send)

    app_mock.assert_called_once()


async def test_memory_fallback_blocks_after_limit() -> None:
    from app.infrastructure.cache.rate_limit import _memory_windows

    _memory_windows.clear()
    redis = MagicMock()
    redis.pipeline = MagicMock(side_effect=Exception("Redis down"))
    key = "rl:mem-block:1.2.3.4"
    assert await redis_rate_check(redis, key, limit=2, window_seconds=60) is True
    assert await redis_rate_check(redis, key, limit=2, window_seconds=60) is True
    assert await redis_rate_check(redis, key, limit=2, window_seconds=60) is False


async def test_ip_ceiling_blocks_unique_bearers_on_mutating_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Уникальный Bearer — новое клиентское ведро; IP-потолок всё равно режет."""
    from tests.conftest import make_oidc_settings

    s = make_oidc_settings(
        api_mutation_rate_limit=100,
        api_mutation_ip_rate_limit=1,
        api_mutation_rate_window_seconds=60,
    )
    monkeypatch.setattr("app.middleware.rate_limit.get_settings", lambda: s)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/api/v1/portal/favorites", headers={"Authorization": "Bearer tok-a"})
        second = await client.post("/api/v1/portal/favorites", headers={"Authorization": "Bearer tok-b"})
    assert first.status_code != 429
    assert second.status_code == 429
    assert second.json().get("code") == "rate_limited"
