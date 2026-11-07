"""Команды /help, /status, /unlink."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.infrastructure.db.models.portal_telegram_binding import PortalTelegramBinding
from app.portal_telegram.bot.handlers.common import cmd_help, cmd_status, cmd_unlink


def _message(*, chat_type: str = "private", chat_id: int = 1) -> MagicMock:
    msg = MagicMock()
    msg.chat = MagicMock()
    msg.chat.type = chat_type
    msg.chat.id = chat_id
    msg.answer = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_cmd_status_rejects_group_chat() -> None:
    msg = _message(chat_type="group", chat_id=1)
    await cmd_status(msg)
    assert "личном чате" in msg.answer.await_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_help_rejects_group_chat() -> None:
    msg = _message(chat_type="group", chat_id=1)
    await cmd_help(msg)
    assert "личном чате" in msg.answer.await_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_unlink_rejects_group_chat() -> None:
    msg = _message(chat_type="group", chat_id=1)
    await cmd_unlink(msg)
    assert "личном чате" in msg.answer.await_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_help_lists_commands() -> None:
    msg = _message()
    await cmd_help(msg)
    text = msg.answer.await_args[0][0]
    assert "/start" in text
    assert "/unlink" in text


@pytest.mark.asyncio
async def test_cmd_status_not_bound(monkeypatch: pytest.MonkeyPatch, sqlite_session) -> None:
    @asynccontextmanager
    async def _sess():
        yield sqlite_session

    monkeypatch.setattr("app.portal_telegram.bot.handlers.common.async_session_factory", lambda: _sess())

    msg = _message(chat_id=1)
    await cmd_status(msg)
    assert "не привязан" in msg.answer.await_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_status_bound(monkeypatch: pytest.MonkeyPatch, sqlite_session) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=900))
    await sqlite_session.commit()

    @asynccontextmanager
    async def _sess():
        yield sqlite_session

    monkeypatch.setattr("app.portal_telegram.bot.handlers.common.async_session_factory", lambda: _sess())

    msg = _message(chat_id=900)
    await cmd_status(msg)
    assert "привязан" in msg.answer.await_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_unlink_when_not_bound(monkeypatch: pytest.MonkeyPatch, sqlite_session) -> None:
    @asynccontextmanager
    async def _sess():
        yield sqlite_session

    monkeypatch.setattr("app.portal_telegram.bot.handlers.common.async_session_factory", lambda: _sess())

    msg = _message(chat_id=777)
    await cmd_unlink(msg)
    assert "не было" in msg.answer.await_args[0][0].lower()


@pytest.mark.asyncio
async def test_cmd_unlink_removes_binding(monkeypatch: pytest.MonkeyPatch, sqlite_session) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=888))
    await sqlite_session.commit()

    @asynccontextmanager
    async def _sess():
        yield sqlite_session

    monkeypatch.setattr("app.portal_telegram.bot.handlers.common.async_session_factory", lambda: _sess())

    msg = _message(chat_id=888)
    await cmd_unlink(msg)
    assert "снята" in msg.answer.await_args[0][0].lower()
