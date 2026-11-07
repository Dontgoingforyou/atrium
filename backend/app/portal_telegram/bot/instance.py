from __future__ import annotations

import logging
from urllib.parse import urlsplit

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from app.portal_telegram.bot.handlers import register_handlers
from app.portal_telegram.constants import TELEGRAM_SESSION_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

_bot: Bot | None = None
_dp: Dispatcher | None = None
_bot_username: str = ""


def _proxy_log_label(proxy_url: str) -> str:
    """Хост прокси без userinfo — в URL может быть пароль SOCKS."""
    parsed = urlsplit(proxy_url)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port is not None else ""
    scheme = parsed.scheme or "proxy"
    if parsed.username:
        return f"{scheme}://***@{host}{port}"
    if host:
        return f"{scheme}://{host}{port}"
    return scheme


def _build_session(proxy_url: str) -> AiohttpSession:
    if not proxy_url:
        return AiohttpSession(timeout=TELEGRAM_SESSION_TIMEOUT_SECONDS)
    try:
        return AiohttpSession(proxy=proxy_url, timeout=TELEGRAM_SESSION_TIMEOUT_SECONDS)
    except Exception:
        logger.warning(
            "Telegram: не удалось создать прокси-сессию (%s), используется прямое подключение",
            _proxy_log_label(proxy_url),
            exc_info=True,
        )
        return AiohttpSession(timeout=TELEGRAM_SESSION_TIMEOUT_SECONDS)


def build_bot_and_dispatcher(token: str, proxy_url: str = "") -> tuple[Bot, Dispatcher]:
    global _bot, _dp
    if _bot is not None and _dp is not None:
        return _bot, _dp
    session = _build_session(proxy_url)
    _bot = Bot(token=token, session=session)
    _dp = Dispatcher()
    register_handlers(_dp)
    logger.info("Telegram Bot и Dispatcher созданы")
    return _bot, _dp


def get_bot() -> Bot:
    if _bot is None:
        raise RuntimeError("Telegram Bot не инициализирован")
    return _bot


def get_dispatcher() -> Dispatcher:
    if _dp is None:
        raise RuntimeError("Telegram Dispatcher не инициализирован")
    return _dp


def set_bot_username(username: str) -> None:
    global _bot_username
    _bot_username = username.strip().lstrip("@")


def get_bot_username() -> str:
    return _bot_username


def reset_bot_singleton() -> None:
    """Для тестов: сброс синглтона."""
    global _bot, _dp, _bot_username
    _bot = None
    _dp = None
    _bot_username = ""


async def close_bot_session() -> None:
    global _bot, _dp
    if _bot is not None:
        await _bot.session.close()
        _bot = None
    _dp = None
    set_bot_username("")
