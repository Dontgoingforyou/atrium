"""Вспомогательные утилиты для тестирования WebSocket-эндпоинтов."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from starlette.testclient import TestClient, WebSocketTestSession


@contextmanager
def websocket_connect_with_ticket(
    client: TestClient,
    path: str,
    ticket: str,
) -> Generator[WebSocketTestSession, None, None]:
    """Подключиться к WS-эндпоинту с тикетом как query-параметром."""
    with client.websocket_connect(f"{path}?ticket={ticket}") as ws:
        yield ws
