"""Сборка stateless HTTP MCP и регистрация тулов."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.types import ASGIApp, Receive, Scope, Send

from app.portal_mcp.auth import McpBearerGate
from app.portal_mcp.constants import MCP_HTTP_BODY_MAX_BYTES

# Портал стоит за nginx: Host публичный, не localhost. Защита SDK режет вызов Hub.
portal_mcp = FastMCP(
    "Космолёт",
    instructions="Портал Космолёт. Тулы доступны администратору и менеджеру от их собственного входа.",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    max_request_body_size=MCP_HTTP_BODY_MAX_BYTES,
)

_tools_registered = False


def build_mcp_app() -> ASGIApp:
    global _tools_registered
    if not _tools_registered:
        from app.portal_mcp.tools import register_tools

        register_tools(portal_mcp)
        _tools_registered = True
    return McpBearerGate(portal_mcp.streamable_http_app())


@asynccontextmanager
async def mcp_session_lifespan() -> AsyncIterator[None]:
    """Держать task group MCP, пока живёт процесс API.

    SDK пускает ``run()`` один раз. Тесты входят в lifespan повторно, поэтому после
    выхода флаг снимается. Если группа уже запущена другим входом, второй не открываем.
    """
    manager = portal_mcp.session_manager
    if getattr(manager, "_task_group", None) is not None:
        yield
        return
    # Предыдущий вход уже вышел: SDK оставляет флаг, а группа пуста.
    if getattr(manager, "_has_started", False):
        setattr(manager, "_has_started", False)
    try:
        async with manager.run():
            yield
    finally:
        if getattr(manager, "_task_group", None) is None:
            setattr(manager, "_has_started", False)


class McpMountSlash:
    """Starlette mount отвечает 307 на ``/api/v1/mcp`` без слэша. Hub шлёт POST без него."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path") == "/api/v1/mcp":
            scope = dict(scope)
            scope["path"] = "/api/v1/mcp/"
            scope["raw_path"] = b"/api/v1/mcp/"
        await self.app(scope, receive, send)
