from __future__ import annotations

import asyncio
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings
from app.portal_telegram.bot.instance import (
    build_bot_and_dispatcher,
    close_bot_session,
    get_bot,
    reset_bot_singleton,
    set_bot_username,
)
from app.portal_telegram.constants import TELEGRAM_POLLING_TIMEOUT_SECONDS
from app.portal_telegram.services.listener import telegram_inbox_listener_loop
from app.portal_telegram.webhook_config import normalize_webhook_path, webhook_secret

logger = logging.getLogger(__name__)


async def init_telegram_bot(redis: aioredis.Redis | None) -> list[asyncio.Task[Any]] | None:
    s = get_settings()
    token = s.telegram_bot_token.strip()
    if not token:
        logger.info("Telegram: токен не задан — бот отключён")
        return None

    bot, dp = build_bot_and_dispatcher(token, proxy_url=s.telegram_proxy_url.strip())
    fallback_username = s.telegram_bot_username.strip().lstrip("@")
    try:
        me = await bot.get_me()
        if me.username:
            set_bot_username(me.username)
        elif fallback_username:
            set_bot_username(fallback_username)
        else:
            set_bot_username("")
            logger.warning(
                "Telegram: у бота нет username в getMe; задайте TELEGRAM_BOT_USERNAME для deep link привязки"
            )
    except Exception:
        logger.warning("Telegram: getMe не удался", exc_info=True)
        if fallback_username:
            set_bot_username(fallback_username)
        else:
            set_bot_username("")

    tasks: list[asyncio.Task[Any]] = []

    if redis is not None:
        tasks.append(asyncio.create_task(telegram_inbox_listener_loop(redis), name="tg-inbox-listener"))
    else:
        logger.warning("Telegram listener не запущен: Redis недоступен")

    if s.telegram_use_polling:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
        except Exception:
            logger.warning(
                "Telegram: delete_webhook не удался — бот может быть недоступен при старте",
                exc_info=True,
            )
        tasks.append(
            asyncio.create_task(
                dp.start_polling(bot, polling_timeout=TELEGRAM_POLLING_TIMEOUT_SECONDS),
                name="tg-polling",
            )
        )
    else:
        base = s.telegram_webhook_base_url.strip().rstrip("/")
        path = normalize_webhook_path(s.telegram_webhook_path)
        if not base:
            logger.error("Telegram webhook: пустой TELEGRAM_WEBHOOK_BASE_URL — setWebhook пропущен")
        else:
            secret = webhook_secret(s)
            url = f"{base}{path}"
            try:
                await bot.set_webhook(url=url, secret_token=secret)
                logger.info("Telegram setWebhook: %s", url)
            except Exception:
                logger.warning("Telegram: setWebhook не удался — бот недоступен при старте", exc_info=True)

    return tasks


async def shutdown_telegram_bot(tasks: list[asyncio.Task[Any]] | None) -> None:
    if tasks:
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    try:
        s = get_settings()
        if s.telegram_bot_token.strip() and not s.telegram_use_polling:
            await get_bot().delete_webhook(drop_pending_updates=False)
    except RuntimeError:
        pass
    except Exception:
        logger.debug("Telegram delete_webhook при остановке", exc_info=True)
    await close_bot_session()
    reset_bot_singleton()
