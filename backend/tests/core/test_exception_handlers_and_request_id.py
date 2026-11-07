"""Контракт exception_handlers и RequestIdMiddleware."""

from __future__ import annotations

from unittest.mock import AsyncMock

from app.api.exception_handlers import register_exception_handlers
from app.core.exceptions import ForbiddenError, NotFoundError, build_error_payload
from app.core.request_context import reset_request_id, set_request_id
from app.main import app
from app.middleware.request_id import RequestIdMiddleware, _extract_request_id
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field


class _EchoIn(BaseModel):
    name: str = Field(min_length=1)


def _handlers_app() -> FastAPI:
    application = FastAPI()
    register_exception_handlers(application)
    application.add_middleware(RequestIdMiddleware)

    @application.get("/nf")
    async def _not_found() -> None:
        raise NotFoundError("Объект не найден")

    @application.get("/fb")
    async def _forbidden() -> None:
        raise ForbiddenError("Нет доступа")

    @application.get("/boom")
    async def _boom() -> None:
        raise RuntimeError("secret-stack-trace")

    @application.get("/teapot")
    async def _teapot() -> None:
        raise HTTPException(status_code=418, detail="teapot")

    @application.post("/echo")
    async def _echo(body: _EchoIn) -> dict[str, str]:
        return {"name": body.name}

    return application


async def test_app_error_not_found_payload() -> None:
    transport = ASGITransport(app=_handlers_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/nf")
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == "not_found"
    assert body["message"] == "Объект не найден"
    assert body.get("request_id")


async def test_app_error_forbidden_payload() -> None:
    transport = ASGITransport(app=_handlers_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/fb")
    assert r.status_code == 403
    body = r.json()
    assert body["code"] == "forbidden"
    assert body["message"] == "Нет доступа"
    assert body.get("request_id")


async def test_unhandled_exception_internal_error_without_traceback() -> None:
    transport = ASGITransport(app=_handlers_app(), raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["code"] == "internal_error"
    assert "секрет" not in body["message"].lower()
    assert "secret-stack-trace" not in r.text
    assert "Traceback" not in r.text
    assert body.get("request_id")


async def test_http_exception_uses_shared_payload() -> None:
    transport = ASGITransport(app=_handlers_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/teapot")
    assert r.status_code == 418
    body = r.json()
    assert body["code"] == "http_418"
    assert body["message"] == "teapot"


async def test_pydantic_422_keeps_fastapi_detail_shape() -> None:
    """Pydantic 422 — тело FastAPI ``detail``, не {code, message} (см. testing.mdc)."""
    transport = ASGITransport(app=_handlers_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/echo", json={"name": ""})
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body
    assert "code" not in body


async def test_request_id_middleware_passes_lifespan_scope() -> None:
    inner = AsyncMock()
    mw = RequestIdMiddleware(inner)
    scope: dict[str, object] = {"type": "lifespan", "asgi": {"version": "3.0"}}
    receive = AsyncMock()
    send = AsyncMock()
    await mw(scope, receive, send)
    inner.assert_awaited_once_with(scope, receive, send)


async def test_health_ok_includes_request_id() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/health", headers={"X-Request-ID": "rid-from-client"})
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers.get("x-request-id") == "rid-from-client"


async def test_health_generates_request_id_when_missing() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/v1/health")
    assert r.status_code == 200
    rid = r.headers.get("x-request-id")
    assert rid is not None and len(rid) >= 8


def test_error_payload_includes_request_id_when_set() -> None:
    token = set_request_id("ctx-rid-99")
    try:
        body = build_error_payload(code="x", message="m")
    finally:
        reset_request_id(token)
    assert body.get("request_id") == "ctx-rid-99"


def test_extract_request_id_missing_header_generates_uuid() -> None:
    rid = _extract_request_id({})
    assert len(rid) == 36


def test_extract_request_id_valid_header_passthrough() -> None:
    rid = _extract_request_id({b"x-request-id": b"client-rid-1"})
    assert rid == "client-rid-1"


def test_extract_request_id_invalid_utf8_falls_back_to_uuid() -> None:
    rid = _extract_request_id({b"x-request-id": b"\xff\xfebad"})
    assert len(rid) == 36


def test_extract_request_id_too_long_falls_back_to_uuid() -> None:
    too_long = ("a" * 500).encode()
    rid = _extract_request_id({b"x-request-id": too_long})
    assert len(rid) == 36


def test_extract_request_id_crlf_falls_back_to_uuid() -> None:
    rid = _extract_request_id({b"x-request-id": b"ok\r\nSet-Cookie: x=1"})
    assert len(rid) == 36
    assert "\r" not in rid
    assert "\n" not in rid


def test_extract_request_id_spaces_and_unicode_fall_back_to_uuid() -> None:
    assert len(_extract_request_id({b"x-request-id": b"rid with spaces"})) == 36
    assert len(_extract_request_id({b"x-request-id": "запрос-1".encode()})) == 36


async def test_request_id_middleware_survives_invalid_utf8_header() -> None:
    async def inner(scope: dict, receive: object, send: object) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    mw = RequestIdMiddleware(inner)  # type: ignore[arg-type]
    scope: dict[str, object] = {"type": "http", "headers": [(b"x-request-id", b"\xff\xfebad")]}
    sent: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    await mw(scope, AsyncMock(), send)

    start = next(m for m in sent if m["type"] == "http.response.start")
    assert start["status"] == 200
    headers = dict(start["headers"])  # type: ignore[arg-type]
    assert headers.get(b"x-request-id") != b"\xff\xfebad"
