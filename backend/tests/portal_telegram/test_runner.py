"""Старт/остановка Telegram-бота (webhook / polling, listener)."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.portal_telegram.bot import runner as runner_mod
from app.portal_telegram.constants import TELEGRAM_POLLING_TIMEOUT_SECONDS


def _make_bot_dp() -> tuple[MagicMock, MagicMock]:
    bot = MagicMock()
    bot.get_me = AsyncMock(return_value=SimpleNamespace(username="FromApiBot"))
    bot.delete_webhook = AsyncMock()
    bot.set_webhook = AsyncMock()
    dp = MagicMock()

    async def _poll(_b: object, **_kwargs: object) -> None:
        await asyncio.Event().wait()

    dp.start_polling = AsyncMock(side_effect=_poll)
    return bot, dp


@pytest.mark.asyncio
async def test_init_telegram_bot_empty_token_returns_none(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    s = tg_settings(telegram_bot_token="")
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    build = MagicMock()
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", build)
    out = await runner_mod.init_telegram_bot(MagicMock())
    assert out is None
    build.assert_not_called()


@pytest.mark.asyncio
async def test_init_polling_delete_webhook_failure_still_starts(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    bot, dp = _make_bot_dp()
    bot.delete_webhook = AsyncMock(side_effect=ConnectionError("proxy down"))
    s = tg_settings(telegram_bot_token="1:T", telegram_use_polling=True)
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))
    monkeypatch.setattr(runner_mod, "telegram_inbox_listener_loop", lambda _r: asyncio.sleep(99999))

    tasks = await runner_mod.init_telegram_bot(MagicMock())
    assert tasks is not None
    assert len(tasks) == 2
    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=True)
    await asyncio.sleep(0)
    dp.start_polling.assert_called()
    assert dp.start_polling.call_args.kwargs.get("polling_timeout") == TELEGRAM_POLLING_TIMEOUT_SECONDS
    await runner_mod.shutdown_telegram_bot(tasks)


@pytest.mark.asyncio
async def test_init_sets_username_from_get_me(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    """После теста close_bot_session вызывается в shutdown — здесь только проверяем вызовы."""
    bot, dp = _make_bot_dp()
    s = tg_settings(telegram_bot_token="1:TOKEN", telegram_use_polling=True)
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))

    async def short_listener(_r: object) -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(runner_mod, "telegram_inbox_listener_loop", short_listener)

    redis = MagicMock()
    tasks = await runner_mod.init_telegram_bot(redis)
    assert tasks is not None
    assert len(tasks) == 2
    bot.get_me.assert_awaited_once()
    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=True)
    await runner_mod.shutdown_telegram_bot(tasks)


@pytest.mark.asyncio
async def test_init_get_me_no_username_uses_fallback(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    bot, dp = _make_bot_dp()
    bot.get_me = AsyncMock(return_value=SimpleNamespace(username=None))
    s = tg_settings(
        telegram_bot_token="1:T",
        telegram_use_polling=True,
        telegram_bot_username="FallbackName",
    )
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))
    monkeypatch.setattr(runner_mod, "telegram_inbox_listener_loop", lambda _r: asyncio.sleep(99999))

    tasks = await runner_mod.init_telegram_bot(MagicMock())
    assert tasks is not None
    from app.portal_telegram.bot.instance import get_bot_username

    assert get_bot_username() == "FallbackName"
    await runner_mod.shutdown_telegram_bot(tasks)


@pytest.mark.asyncio
async def test_init_get_me_no_username_no_fallback_logs(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    bot, dp = _make_bot_dp()
    bot.get_me = AsyncMock(return_value=SimpleNamespace(username=""))
    s = tg_settings(telegram_bot_token="1:T", telegram_use_polling=True, telegram_bot_username="")
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))
    monkeypatch.setattr(runner_mod, "telegram_inbox_listener_loop", lambda _r: asyncio.sleep(99999))

    tasks = await runner_mod.init_telegram_bot(MagicMock())
    assert tasks is not None
    from app.portal_telegram.bot.instance import get_bot_username

    assert get_bot_username() == ""
    await runner_mod.shutdown_telegram_bot(tasks)


@pytest.mark.asyncio
async def test_init_get_me_exception_uses_fallback(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    bot, dp = _make_bot_dp()
    bot.get_me = AsyncMock(side_effect=ConnectionError("tg down"))
    s = tg_settings(
        telegram_bot_token="1:T",
        telegram_use_polling=True,
        telegram_bot_username="AfterError",
    )
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))
    monkeypatch.setattr(runner_mod, "telegram_inbox_listener_loop", lambda _r: asyncio.sleep(99999))

    tasks = await runner_mod.init_telegram_bot(MagicMock())
    assert tasks is not None
    from app.portal_telegram.bot.instance import get_bot_username

    assert get_bot_username() == "AfterError"
    await runner_mod.shutdown_telegram_bot(tasks)


@pytest.mark.asyncio
async def test_init_get_me_exception_no_fallback(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    bot, dp = _make_bot_dp()
    bot.get_me = AsyncMock(side_effect=RuntimeError("fail"))
    s = tg_settings(telegram_bot_token="1:T", telegram_use_polling=True, telegram_bot_username="")
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))
    monkeypatch.setattr(runner_mod, "telegram_inbox_listener_loop", lambda _r: asyncio.sleep(99999))

    tasks = await runner_mod.init_telegram_bot(MagicMock())
    assert tasks is not None
    from app.portal_telegram.bot.instance import get_bot_username

    assert get_bot_username() == ""
    await runner_mod.shutdown_telegram_bot(tasks)


@pytest.mark.asyncio
async def test_init_redis_none_skips_listener_task(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    bot, dp = _make_bot_dp()
    s = tg_settings(telegram_bot_token="1:T", telegram_use_polling=True)
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))

    tasks = await runner_mod.init_telegram_bot(None)
    assert tasks is not None
    assert len(tasks) == 1
    names = [t.get_name() for t in tasks]
    assert "tg-polling" in names
    assert "tg-inbox-listener" not in names
    await runner_mod.shutdown_telegram_bot(tasks)


@pytest.mark.asyncio
async def test_init_webhook_mode_set_webhook(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    bot, dp = _make_bot_dp()
    s = tg_settings(
        telegram_bot_token="1:T",
        telegram_use_polling=False,
        telegram_webhook_base_url="https://api.example",
        telegram_webhook_path="/hook",
        telegram_webhook_secret="whsec",
    )
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))
    monkeypatch.setattr(runner_mod, "telegram_inbox_listener_loop", lambda _r: asyncio.sleep(99999))

    tasks = await runner_mod.init_telegram_bot(MagicMock())
    assert tasks is not None
    bot.set_webhook.assert_awaited_once()
    call_kw = bot.set_webhook.await_args.kwargs
    assert call_kw["url"] == "https://api.example/hook"
    assert call_kw["secret_token"] == "whsec"
    bot.delete_webhook.assert_not_awaited()
    monkeypatch.setattr(runner_mod, "get_bot", lambda: bot)
    await runner_mod.shutdown_telegram_bot(tasks)


@pytest.mark.asyncio
async def test_init_webhook_empty_base_skips_set_webhook(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    bot, dp = _make_bot_dp()
    s = tg_settings(
        telegram_bot_token="1:T",
        telegram_use_polling=False,
        telegram_webhook_base_url="",
        telegram_webhook_path="/hook",
    )
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))
    monkeypatch.setattr(runner_mod, "telegram_inbox_listener_loop", lambda _r: asyncio.sleep(99999))

    tasks = await runner_mod.init_telegram_bot(MagicMock())
    assert tasks is not None
    bot.set_webhook.assert_not_awaited()
    monkeypatch.setattr(runner_mod, "get_bot", lambda: bot)
    await runner_mod.shutdown_telegram_bot(tasks)


@pytest.mark.asyncio
async def test_init_webhook_normalizes_path(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    bot, dp = _make_bot_dp()
    s = tg_settings(
        telegram_bot_token="1:T",
        telegram_use_polling=False,
        telegram_webhook_base_url="https://x",
        telegram_webhook_path="no-slash",
    )
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))
    monkeypatch.setattr(runner_mod, "telegram_inbox_listener_loop", lambda _r: asyncio.sleep(99999))

    tasks = await runner_mod.init_telegram_bot(MagicMock())
    assert tasks is not None
    assert bot.set_webhook.await_args.kwargs["url"] == "https://x/no-slash"
    monkeypatch.setattr(runner_mod, "get_bot", lambda: bot)
    await runner_mod.shutdown_telegram_bot(tasks)


@pytest.mark.asyncio
async def test_shutdown_tasks_none_completes(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    monkeypatch.setattr(runner_mod, "get_settings", lambda: tg_settings(telegram_bot_token=""))
    await runner_mod.shutdown_telegram_bot(None)


@pytest.mark.asyncio
async def test_shutdown_webhook_calls_delete_webhook(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    bot, dp = _make_bot_dp()
    s = tg_settings(
        telegram_bot_token="1:T",
        telegram_use_polling=False,
        telegram_webhook_base_url="https://h",
        telegram_webhook_path="/p",
    )
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))
    monkeypatch.setattr(runner_mod, "telegram_inbox_listener_loop", lambda _r: asyncio.sleep(99999))

    tasks = await runner_mod.init_telegram_bot(MagicMock())
    monkeypatch.setattr(runner_mod, "get_bot", lambda: bot)
    await runner_mod.shutdown_telegram_bot(tasks)

    bot.delete_webhook.assert_awaited()
    last = bot.delete_webhook.await_args_list[-1]
    assert last.kwargs.get("drop_pending_updates") is False


@pytest.mark.asyncio
async def test_shutdown_get_bot_runtime_error_swallowed(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    """Строка except RuntimeError в shutdown при отсутствии бота после reset."""
    s = tg_settings(telegram_bot_token="1:T", telegram_use_polling=False)
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "get_bot", lambda: (_ for _ in ()).throw(RuntimeError("no bot")))
    await runner_mod.shutdown_telegram_bot(None)


@pytest.mark.asyncio
async def test_shutdown_cancels_tasks(monkeypatch: pytest.MonkeyPatch, tg_settings) -> None:
    bot, dp = _make_bot_dp()
    s = tg_settings(telegram_bot_token="1:T", telegram_use_polling=True)
    monkeypatch.setattr(runner_mod, "get_settings", lambda: s)
    monkeypatch.setattr(runner_mod, "build_bot_and_dispatcher", lambda _t, **_kw: (bot, dp))

    async def hanging_listener(_r: object) -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(runner_mod, "telegram_inbox_listener_loop", hanging_listener)

    redis = MagicMock()
    tasks = await runner_mod.init_telegram_bot(redis)
    assert tasks is not None
    await runner_mod.shutdown_telegram_bot(tasks)
