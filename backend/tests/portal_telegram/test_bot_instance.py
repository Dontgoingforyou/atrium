"""Синглтон Bot/Dispatcher."""

from __future__ import annotations

import pytest
from app.portal_telegram.bot.instance import (
    _proxy_log_label,
    build_bot_and_dispatcher,
    close_bot_session,
    get_bot,
    get_bot_username,
    get_dispatcher,
    reset_bot_singleton,
    set_bot_username,
)
from app.portal_telegram.constants import TELEGRAM_SESSION_TIMEOUT_SECONDS


def test_proxy_log_label_strips_userinfo() -> None:
    assert _proxy_log_label("socks5://user:secret@host.example:1081") == "socks5://***@host.example:1081"
    assert _proxy_log_label("socks5://telegram-awg:1080") == "socks5://telegram-awg:1080"


@pytest.mark.asyncio
async def test_bot_session_uses_long_poll_timeout() -> None:
    reset_bot_singleton()
    bot, _dp = build_bot_and_dispatcher("123456:FAKE_TOKEN_FOR_TESTS")
    assert bot.session.timeout == TELEGRAM_SESSION_TIMEOUT_SECONDS
    await close_bot_session()


@pytest.mark.asyncio
async def test_build_bot_and_dispatcher_creates_singletons() -> None:
    bot, dp = build_bot_and_dispatcher("123456:FAKE_TOKEN_FOR_TESTS")
    assert bot is get_bot()
    assert dp is get_dispatcher()
    await close_bot_session()


@pytest.mark.asyncio
async def test_build_bot_and_dispatcher_returns_existing_singletons() -> None:
    b1, d1 = build_bot_and_dispatcher("123456:FAKE_TOKEN_FOR_TESTS")
    b2, d2 = build_bot_and_dispatcher("123456:OTHER")
    assert b1 is b2
    assert d1 is d2
    await close_bot_session()


def test_get_bot_raises_without_init() -> None:
    reset_bot_singleton()
    with pytest.raises(RuntimeError, match="Telegram Bot не инициализирован"):
        get_bot()


def test_get_dispatcher_raises_without_init() -> None:
    reset_bot_singleton()
    with pytest.raises(RuntimeError, match="Telegram Dispatcher не инициализирован"):
        get_dispatcher()


def test_set_get_bot_username_strips_at() -> None:
    reset_bot_singleton()
    set_bot_username("@MyBot")
    assert get_bot_username() == "MyBot"


@pytest.mark.asyncio
async def test_reset_bot_singleton_clears_state() -> None:
    build_bot_and_dispatcher("123456:FAKE_TOKEN_FOR_TESTS")
    reset_bot_singleton()
    with pytest.raises(RuntimeError):
        get_bot()


@pytest.mark.asyncio
async def test_close_bot_session_resets() -> None:
    build_bot_and_dispatcher("123456:FAKE_TOKEN_FOR_TESTS")
    set_bot_username("x")
    await close_bot_session()
    with pytest.raises(RuntimeError):
        get_bot()
    assert get_bot_username() == ""
