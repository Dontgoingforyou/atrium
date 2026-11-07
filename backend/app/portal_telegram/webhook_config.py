"""Единый источник правды для секрета и пути Telegram-вебхука.

Используется и проверкой входящего запроса (``webhook.py``), и регистрацией
``setWebhook`` при старте (``bot/runner.py``) — секрет и путь должны совпадать
в обоих местах, иначе Telegram не сможет достучаться до вебхука.
"""

from __future__ import annotations

import hashlib
import logging

from app.core.config import Settings

logger = logging.getLogger(__name__)


def normalize_webhook_path(raw: str) -> str:
    p = raw.strip()
    if not p.startswith("/"):
        p = "/" + p
    return p


def webhook_secret(settings: Settings) -> str:
    explicit = settings.telegram_webhook_secret.strip()
    if explicit:
        return explicit
    # Запасной вариант: производный от токена бота.
    if not settings.debug:
        logger.warning(
            "TELEGRAM_WEBHOOK_SECRET не задан — используется производный от bot_token секрет. "
            "Задайте TELEGRAM_WEBHOOK_SECRET в .env для независимого ротирования."
        )
    token = settings.telegram_bot_token.strip()
    return hashlib.sha256(token.encode()).hexdigest()[:32]
