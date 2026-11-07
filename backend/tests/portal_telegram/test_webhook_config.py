"""Единый источник секрета и пути Telegram-вебхука (webhook.py + bot/runner.py)."""

from __future__ import annotations

import hashlib

from app.portal_telegram import webhook_config


def test_webhook_secret_explicit(tg_settings) -> None:
    s = tg_settings(telegram_webhook_secret="  my-secret  ", telegram_bot_token="1:x")
    assert webhook_config.webhook_secret(s) == "my-secret"


def test_webhook_secret_derived_from_token(tg_settings) -> None:
    s = tg_settings(telegram_webhook_secret="", telegram_bot_token="999:ABC")
    expected = hashlib.sha256(b"999:ABC").hexdigest()[:32]
    assert webhook_config.webhook_secret(s) == expected


def test_normalize_webhook_path_adds_leading_slash() -> None:
    assert webhook_config.normalize_webhook_path("tg/hook") == "/tg/hook"


def test_normalize_webhook_path_keeps_leading_slash() -> None:
    assert webhook_config.normalize_webhook_path("/tg/hook") == "/tg/hook"


def test_normalize_webhook_path_strips_whitespace() -> None:
    assert webhook_config.normalize_webhook_path("  /tg/hook  ") == "/tg/hook"
