from __future__ import annotations

from aiogram import Dispatcher

from app.portal_telegram.bot.handlers import common, start


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(common.router)
