from __future__ import annotations

from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

_SECURITY_HEADERS: list[tuple[bytes, bytes]] = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"strict-origin-when-cross-origin"),
    (b"x-xss-protection", b"0"),
    # Запрещаем доступ к чувствительным браузерным API, не используемым порталом.
    (b"permissions-policy", b"camera=(), microphone=(), geolocation=(), interest-cohort=()"),
    # Content-Security-Policy требует nonce-стратегии из-за inline-скриптов Swagger/ReDoc;
    # рекомендуется настраивать на уровне reverse proxy (Nginx) для SPA-оболочки.
]

_HSTS_HEADER: tuple[bytes, bytes] = (
    b"strict-transport-security",
    b"max-age=31536000; includeSubDomains",
)

_CACHE_CONTROL_NO_STORE: tuple[bytes, bytes] = (b"cache-control", b"no-store")


def _overwrite_managed_headers(
    existing: list[tuple[bytes, bytes]],
    extra: list[tuple[bytes, bytes]],
) -> list[tuple[bytes, bytes]]:
    """Заменить управляемые security-заголовки своими значениями (first-wins в браузере)."""
    managed = {name.lower() for name, _ in extra}
    kept = [(name, value) for name, value in existing if name.lower() not in managed]
    kept.extend(extra)
    return kept


class SecurityHeadersMiddleware:
    """Добавляет базовые security-заголовки ко всем HTTP-ответам.

    В debug-режиме HSTS не выставляется (local http://), в production — включён.
    Для ``/api/v1/*`` без своего Cache-Control ставится ``no-store`` (кэш аватаров не трогаем).
    """

    def __init__(self, app: ASGIApp, *, debug: bool = False) -> None:
        self.app = app
        self.debug = debug

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        is_api_v1 = isinstance(path, str) and path.startswith("/api/v1/")

        async def send_with_security_headers(message: Any) -> None:
            if message["type"] == "http.response.start":
                extra = list(_SECURITY_HEADERS)
                if not self.debug:
                    extra.append(_HSTS_HEADER)
                headers = _overwrite_managed_headers(list(message.get("headers", [])), extra)
                if is_api_v1 and not any(name.lower() == b"cache-control" for name, _ in headers):
                    headers.append(_CACHE_CONTROL_NO_STORE)
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_security_headers)
