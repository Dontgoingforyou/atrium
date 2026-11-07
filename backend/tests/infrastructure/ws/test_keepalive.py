"""Тесты утилиты keepalive (app.infrastructure.ws.keepalive)."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from unittest.mock import AsyncMock

import pytest
from app.infrastructure.ws.constants import WS_PING_MESSAGE
from app.infrastructure.ws.keepalive import is_pong, ws_keepalive
from starlette.websockets import WebSocketState


async def _wait_until(pred: Callable[[], bool], *, timeout: float = 1.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if pred():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("условие не выполнилось за отведённое время")


@pytest.mark.parametrize(
    "text",
    [
        '{"type":"pong"}',
        '{"type": "pong"}',
        '{"type":"pong","extra":"ignored"}',
    ],
)
def test_is_pong_valid(text: str) -> None:
    assert is_pong(text) is True


@pytest.mark.parametrize(
    "text",
    [
        '{"type":"ping"}',
        '{"type":"message","text":"hi"}',
        "{}",
        "not json at all",
        "",
        '{"type": null}',
    ],
)
def test_is_pong_invalid(text: str) -> None:
    assert is_pong(text) is False


async def test_ws_keepalive_sends_ping() -> None:
    ws = AsyncMock()
    ws.client_state = WebSocketState.CONNECTED
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()

    async with ws_keepalive(ws, interval=0, timeout=2) as ka:
        await _wait_until(lambda: ws.send_text.await_count >= 1)
        ws.send_text.assert_awaited_with(WS_PING_MESSAGE)
        ka.notify_pong()


async def test_ws_keepalive_pong_prevents_close() -> None:
    ws = AsyncMock()
    ws.client_state = WebSocketState.CONNECTED
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()

    async with ws_keepalive(ws, interval=0, timeout=0.4) as ka:
        await _wait_until(lambda: ws.send_text.await_count >= 1)

        async def _keep_pong() -> None:
            while True:
                ka.notify_pong()
                await asyncio.sleep(0.02)

        pong_task = asyncio.create_task(_keep_pong())
        try:
            await asyncio.sleep(0.25)
            ws.close.assert_not_called()
        finally:
            pong_task.cancel()


async def test_ws_keepalive_closes_on_pong_timeout() -> None:
    ws = AsyncMock()
    ws.client_state = WebSocketState.CONNECTED
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()

    async with ws_keepalive(ws, interval=0, timeout=0.05):
        await _wait_until(lambda: ws.close.await_count >= 1)

    ws.close.assert_awaited_with(code=1001)


async def test_ws_keepalive_no_ping_when_disconnected() -> None:
    ws = AsyncMock()
    ws.client_state = WebSocketState.DISCONNECTED
    ws.send_text = AsyncMock()

    async with ws_keepalive(ws, interval=0, timeout=1):
        await asyncio.sleep(0.05)

    ws.send_text.assert_not_called()


async def test_ws_keepalive_send_error_does_not_raise() -> None:
    ws = AsyncMock()
    ws.client_state = WebSocketState.CONNECTED
    ws.send_text = AsyncMock(side_effect=RuntimeError("WS closed"))
    ws.close = AsyncMock()

    async with ws_keepalive(ws, interval=0, timeout=1):
        await _wait_until(lambda: ws.send_text.await_count >= 1)
        await asyncio.sleep(0.05)

    ws.send_text.assert_awaited()
    ws.close.assert_not_called()


async def test_ws_keepalive_cancels_on_exception() -> None:
    ws = AsyncMock()
    ws.client_state = WebSocketState.CONNECTED

    with pytest.raises(ValueError, match="test error"):
        async with ws_keepalive(ws, interval=999, timeout=10):
            raise ValueError("test error")
