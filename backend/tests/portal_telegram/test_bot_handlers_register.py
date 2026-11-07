"""Регистрация роутеров aiogram."""

from __future__ import annotations

from aiogram import Dispatcher
from app.portal_telegram.bot.handlers import register_handlers


def test_register_handlers_includes_start_and_common() -> None:
    dp = Dispatcher()
    register_handlers(dp)
    names = [getattr(r, "name", "") for r in dp.sub_routers]
    assert len(dp.sub_routers) >= 2
    assert "tg_start" in names
    assert "tg_common" in names
