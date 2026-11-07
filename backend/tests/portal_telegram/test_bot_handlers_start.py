"""Обработчик /start."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.portal_telegram.bot.handlers.start import cmd_start


def _message(*, chat_type: str = "private", chat_id: int = 1) -> MagicMock:
    msg = MagicMock()
    msg.chat = MagicMock()
    msg.chat.type = chat_type
    msg.chat.id = chat_id
    msg.answer = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_cmd_start_without_code_replies_hint() -> None:
    msg = _message()
    cmd = MagicMock()
    cmd.args = None
    await cmd_start(msg, cmd)
    msg.answer.assert_awaited_once()
    assert "привязать" in msg.answer.await_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_start_rejects_group_chat() -> None:
    msg = _message(chat_type="group")
    cmd = MagicMock()
    cmd.args = "tgb_secret"
    await cmd_start(msg, cmd)
    msg.answer.assert_awaited_once()
    assert "личном чате" in msg.answer.await_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_start_rejects_supergroup_chat() -> None:
    msg = _message(chat_type="supergroup")
    cmd = MagicMock()
    cmd.args = "tgb_secret"
    await cmd_start(msg, cmd)
    assert "личном чате" in msg.answer.await_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_start_rejects_channel_chat() -> None:
    msg = _message(chat_type="channel")
    cmd = MagicMock()
    cmd.args = "tgb_secret"
    await cmd_start(msg, cmd)
    assert "личном чате" in msg.answer.await_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_start_without_redis(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.portal_telegram.bot.handlers.start.get_redis_client", lambda: None)
    msg = _message()
    cmd = MagicMock()
    cmd.args = "tgb_x"
    await cmd_start(msg, cmd)
    msg.answer.assert_awaited_once()
    assert "Redis" in msg.answer.await_args[0][0]


@pytest.mark.asyncio
async def test_cmd_start_invalid_code(monkeypatch: pytest.MonkeyPatch, sqlite_session) -> None:
    redis = MagicMock()
    redis.getdel = AsyncMock(return_value=None)
    monkeypatch.setattr("app.portal_telegram.bot.handlers.start.get_redis_client", lambda: redis)

    @asynccontextmanager
    async def _sess():
        yield sqlite_session

    monkeypatch.setattr("app.portal_telegram.bot.handlers.start.async_session_factory", lambda: _sess())

    msg = _message()
    cmd = MagicMock()
    cmd.args = "tgb_bad"
    await cmd_start(msg, cmd)
    msg.answer.assert_awaited_once()
    assert "Код" in msg.answer.await_args[0][0]


@pytest.mark.asyncio
async def test_cmd_start_confirm_generic_error(monkeypatch: pytest.MonkeyPatch, sqlite_session) -> None:
    redis = MagicMock()
    redis.getdel = AsyncMock(return_value="user-sub")
    redis.delete = AsyncMock()
    monkeypatch.setattr("app.portal_telegram.bot.handlers.start.get_redis_client", lambda: redis)

    @asynccontextmanager
    async def _sess():
        yield sqlite_session

    monkeypatch.setattr("app.portal_telegram.bot.handlers.start.async_session_factory", lambda: _sess())

    async def boom(*_a: object, **_kw: object) -> None:
        raise RuntimeError("db down")

    monkeypatch.setattr("app.portal_telegram.bot.handlers.start.confirm_bind", boom)

    msg = _message(chat_id=111)
    cmd = MagicMock()
    cmd.args = "tgb_ok"
    await cmd_start(msg, cmd)
    msg.answer.assert_awaited_once()
    assert "Не удалось" in msg.answer.await_args[0][0]


@pytest.mark.asyncio
async def test_cmd_start_success(monkeypatch: pytest.MonkeyPatch, sqlite_session) -> None:
    redis = MagicMock()
    redis.getdel = AsyncMock(return_value="user-sub")
    redis.delete = AsyncMock()
    monkeypatch.setattr("app.portal_telegram.bot.handlers.start.get_redis_client", lambda: redis)

    @asynccontextmanager
    async def _sess():
        yield sqlite_session

    monkeypatch.setattr("app.portal_telegram.bot.handlers.start.async_session_factory", lambda: _sess())

    msg = _message(chat_id=424242)
    cmd = MagicMock()
    cmd.args = "tgb_good"
    await cmd_start(msg, cmd)
    msg.answer.assert_awaited_once()
    assert "привязан" in msg.answer.await_args[0][0].lower()
