from __future__ import annotations

import re
import uuid
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.request_context import reset_request_id, set_request_id

# Клиентский X-Request-ID — недоверенный вход: только безопасный ASCII-набор,
# чтобы не отражать CR/LF (риск 500 у ASGI-сервера) и мусор в логах/заголовках.
_MAX_CLIENT_REQUEST_ID_LEN = 200
_REQUEST_ID_RE = re.compile(rb"^[A-Za-z0-9._-]{1,200}$")


def _extract_request_id(headers: dict[bytes, bytes]) -> str:
    """Достаёт X-Request-ID из заголовков запроса, генерирует UUID4 при отсутствии/невалидности.

    Значение от клиента — недоверенный вход: байты могут быть не-UTF-8, произвольно
    длинными или содержать CR/LF и прочие символы вне allowlist — в этих случаях
    откатываемся на сгенерированный UUID, а не роняем обработку запроса.
    """
    raw = headers.get(b"x-request-id")
    if not raw or len(raw) > _MAX_CLIENT_REQUEST_ID_LEN:
        return str(uuid.uuid4())
    if _REQUEST_ID_RE.fullmatch(raw) is None:
        return str(uuid.uuid4())
    try:
        decoded = raw.decode("ascii")
    except UnicodeDecodeError:
        return str(uuid.uuid4())
    return decoded or str(uuid.uuid4())


class RequestIdMiddleware:
    """
    Чистый ASGI-middleware (без BaseHTTPMiddleware).
    Читает X-Request-ID из входящего запроса или генерирует UUID4.
    Устанавливает значение в contextvars (доступно всем логгерам в этом запросе).
    Добавляет X-Request-ID в заголовки ответа.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers: dict[bytes, bytes] = dict(scope.get("headers", []))
        request_id = _extract_request_id(headers)
        token = set_request_id(request_id)

        async def send_with_request_id(message: Any) -> None:
            if message["type"] == "http.response.start":
                existing = [
                    (name, value) for name, value in message.get("headers", []) if name.lower() != b"x-request-id"
                ]
                existing.append((b"x-request-id", request_id.encode("ascii")))
                message = {**message, "headers": existing}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            reset_request_id(token)
