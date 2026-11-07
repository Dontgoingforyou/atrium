"""Security-заголовки: точные значения и граница Cache-Control."""

from __future__ import annotations

from unittest.mock import AsyncMock

from app.main import app
from app.middleware.security_headers import SecurityHeadersMiddleware
from httpx import ASGITransport, AsyncClient


async def _run(middleware: SecurityHeadersMiddleware, scope: dict[str, object]) -> dict[bytes, bytes]:
    sent: list[dict[str, object]] = []

    async def inner(_scope: dict, _receive: object, send: object) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware.app = inner  # type: ignore[assignment]
    sent = []

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    await middleware(scope, AsyncMock(), send)
    start = next(m for m in sent if m["type"] == "http.response.start")
    return dict(start["headers"])  # type: ignore[arg-type]


async def test_adds_base_security_headers_on_http_response() -> None:
    middleware = SecurityHeadersMiddleware(AsyncMock(), debug=False)
    headers = await _run(middleware, {"type": "http"})

    assert headers[b"x-content-type-options"] == b"nosniff"
    assert headers[b"x-frame-options"] == b"DENY"
    assert headers[b"referrer-policy"] == b"strict-origin-when-cross-origin"
    assert headers[b"x-xss-protection"] == b"0"
    assert headers[b"permissions-policy"] == b"camera=(), microphone=(), geolocation=(), interest-cohort=()"


async def test_adds_hsts_outside_debug() -> None:
    middleware = SecurityHeadersMiddleware(AsyncMock(), debug=False)
    headers = await _run(middleware, {"type": "http"})

    assert headers[b"strict-transport-security"] == b"max-age=31536000; includeSubDomains"


async def test_skips_hsts_in_debug() -> None:
    middleware = SecurityHeadersMiddleware(AsyncMock(), debug=True)
    headers = await _run(middleware, {"type": "http"})

    assert b"strict-transport-security" not in headers


async def test_passes_through_non_http_scope_untouched() -> None:
    inner = AsyncMock()
    middleware = SecurityHeadersMiddleware(inner, debug=False)
    scope: dict[str, object] = {"type": "websocket"}
    receive = AsyncMock()
    send = AsyncMock()

    await middleware(scope, receive, send)

    inner.assert_awaited_once_with(scope, receive, send)


async def test_overwrites_weaker_frame_options_from_downstream() -> None:
    """Политика приложения жёстче: не оставляем первый (слабый) X-Frame-Options."""

    async def inner(_scope: dict, _receive: object, send: object) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"x-frame-options", b"SAMEORIGIN")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = SecurityHeadersMiddleware(inner, debug=False)
    sent: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    await middleware({"type": "http"}, AsyncMock(), send)
    start = next(m for m in sent if m["type"] == "http.response.start")
    headers = list(start["headers"])  # type: ignore[arg-type]
    frame_values = [value for name, value in headers if name == b"x-frame-options"]
    assert frame_values == [b"DENY"]


async def test_adds_no_store_cache_control_on_api_v1_when_absent() -> None:
    middleware = SecurityHeadersMiddleware(AsyncMock(), debug=False)
    headers = await _run(middleware, {"type": "http", "path": "/api/v1/health"})
    assert headers[b"cache-control"] == b"no-store"


async def test_preserves_existing_cache_control_on_api_v1() -> None:
    async def inner(_scope: dict, _receive: object, send: object) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"cache-control", b"private, max-age=3600")],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    middleware = SecurityHeadersMiddleware(inner, debug=False)
    sent: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    await middleware({"type": "http", "path": "/api/v1/portal/users/user-sub/photo"}, AsyncMock(), send)
    start = next(m for m in sent if m["type"] == "http.response.start")
    headers = dict(start["headers"])  # type: ignore[arg-type]
    assert headers[b"cache-control"] == b"private, max-age=3600"


async def test_does_not_force_no_store_outside_api_v1() -> None:
    middleware = SecurityHeadersMiddleware(AsyncMock(), debug=False)
    headers = await _run(middleware, {"type": "http", "path": "/docs"})
    assert b"cache-control" not in headers


async def test_http_health_has_security_headers() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"
