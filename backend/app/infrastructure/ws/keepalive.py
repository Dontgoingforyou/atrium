"""Server-side keepalive для WebSocket-соединений.

Keepalive-задача периодически отправляет {"type":"ping"} и закрывает соединение,
если клиент не ответил {"type":"pong"} за WS_PING_TIMEOUT секунд.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import WebSocket
from starlette.websockets import WebSocketState

from app.infrastructure.ws.constants import (
    WS_PING_INTERVAL,
    WS_PING_MESSAGE,
    WS_PING_TIMEOUT,
    WS_PONG_TYPE,
)

logger = logging.getLogger(__name__)


class _KeepaliveTask:
    """Фоновая задача: периодические ping/pong для одного WS-соединения."""

    def __init__(self, websocket: WebSocket, interval: int, timeout: int) -> None:
        self._ws = websocket
        self._interval = interval
        self._timeout = timeout
        self._pong_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="ws-keepalive")

    def cancel(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()

    def notify_pong(self) -> None:
        """Вызывать из основного цикла при получении сообщения {"type":"pong"}."""
        self._pong_event.set()

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            if self._ws.client_state != WebSocketState.CONNECTED:
                return
            try:
                await self._ws.send_text(WS_PING_MESSAGE)
            except Exception as exc:
                logger.debug("keepalive: не удалось отправить ping: %s", exc)
                return

            self._pong_event.clear()
            try:
                await asyncio.wait_for(self._pong_event.wait(), timeout=self._timeout)
            except TimeoutError:
                logger.info(
                    "keepalive: клиент не ответил на ping за %ds, закрываем соединение",
                    self._timeout,
                )
                with contextlib.suppress(Exception):
                    await self._ws.close(code=1001)
                return


@contextlib.asynccontextmanager
async def ws_keepalive(
    websocket: WebSocket,
    *,
    interval: int = WS_PING_INTERVAL,
    timeout: int = WS_PING_TIMEOUT,
) -> AsyncGenerator[_KeepaliveTask, None]:
    """Контекстный менеджер: запускает keepalive-задачу на время жизни обработчика.

    Возвращает объект _KeepaliveTask — вызывайте task.notify_pong() при получении
    {"type":"pong"} от клиента.

    Пример обработки pong:

        async with ws_keepalive(websocket) as ka:
            try:
                while True:
                    raw = await websocket.receive_text()
                    msg = json.loads(raw)
                    if msg.get("type") == "pong":
                        ka.notify_pong()
                        continue
                    # ... обработка остальных сообщений ...
            except WebSocketDisconnect:
                ...
    """
    task = _KeepaliveTask(websocket, interval=interval, timeout=timeout)
    task.start()
    try:
        yield task
    finally:
        task.cancel()


def is_pong(raw_text: str) -> bool:
    """Быстрая проверка: является ли текстовое сообщение pong-ответом клиента."""
    try:
        return bool(json.loads(raw_text).get("type") == WS_PONG_TYPE)
    except (ValueError, AttributeError):
        return False
