"""Фикстуры для тестов домена portal_telegram."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Bot
from app.core.config import Settings
from app.portal_telegram.bot.instance import reset_bot_singleton
from httpx import Response
from tests.conftest import make_oidc_settings

TELEGRAM_BIND_API = "/api/v1/telegram/bind"


def assert_api_error(response: Response, status: int, code: str) -> None:
    """Ошибка AppError: и HTTP-статус, и контрактный `code`."""
    assert response.status_code == status, response.text
    assert response.json()["code"] == code


def _detach_telegram_handler_routers() -> None:
    """Снимаем module-level Router с Dispatcher (иначе повторный include_router падает)."""
    from app.portal_telegram.bot.handlers import common, start

    for router in (start.router, common.router):
        parent = router.parent_router
        if parent is not None and router in parent.sub_routers:
            parent.sub_routers.remove(router)
        object.__setattr__(router, "_parent_router", None)


@pytest.fixture(autouse=True)
def reset_telegram_singletons() -> Iterator[None]:
    """Разрываем утечку глобального Bot/Dispatcher между тестами."""
    reset_bot_singleton()
    _detach_telegram_handler_routers()
    yield
    _detach_telegram_handler_routers()
    reset_bot_singleton()


@pytest.fixture
def tg_settings() -> Callable[..., Settings]:
    """Настройки с SSO и полями Telegram для юнит-тестов."""

    def _factory(**kwargs: Any) -> Settings:
        defaults: dict[str, Any] = {
            "telegram_bot_token": "123:FAKE",
            "telegram_use_polling": True,
            "telegram_webhook_base_url": "",
            "telegram_webhook_path": "/tg-hook",
            "telegram_webhook_secret": "",
            "telegram_bot_username": "",
            "portal_public_url": "https://portal.example",
        }
        defaults.update(kwargs)
        return make_oidc_settings(**defaults)

    return _factory


@pytest.fixture
def mock_aiogram_bot() -> MagicMock:
    """Мок Bot API без обращения к сети."""
    bot = MagicMock(spec=Bot)
    bot.send_message = AsyncMock()
    bot.get_me = AsyncMock()
    bot.set_webhook = AsyncMock()
    bot.delete_webhook = AsyncMock()
    bot.session = MagicMock()
    bot.session.close = AsyncMock()
    return bot


class _FakePubSub:
    """Упрощённый pubsub для тестов telegram_inbox_listener_loop."""

    def __init__(self, listen_messages: list[dict[str, Any]]) -> None:
        self._listen_messages = listen_messages
        self.psubscribe = AsyncMock()

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        for msg in self._listen_messages:
            yield msg
        while True:
            await asyncio.sleep(3600)


class _PubSubContext:
    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self._messages = messages

    async def __aenter__(self) -> _FakePubSub:
        return _FakePubSub(self._messages)

    async def __aexit__(self, *_exc: object) -> None:
        return None


class FakeRedisPubSubClient:
    """Redis с подменяемым pubsub(); контекстный менеджер как у redis.asyncio."""

    def __init__(self, listen_messages: list[dict[str, Any]]) -> None:
        self._listen_messages = listen_messages

    def pubsub(self) -> _PubSubContext:
        return _PubSubContext(self._listen_messages)


@pytest.fixture
def patch_telegram_bind_env(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=None)
    fake_redis.set = AsyncMock(return_value=True)

    monkeypatch.setattr("app.portal_telegram.routes.telegram.get_redis_client", lambda: fake_redis)
    monkeypatch.setattr("app.portal_telegram.routes.telegram.get_bot_username", lambda: "AtriumTestBot")

    base = make_oidc_settings(telegram_bot_token="123:FAKE", telegram_use_polling=True)
    monkeypatch.setattr("app.portal_telegram.routes.telegram.get_settings", lambda: base)


@pytest.fixture
def fake_redis_pubsub_factory() -> Callable[[list[dict[str, Any]]], FakeRedisPubSubClient]:
    def _make(messages: list[dict[str, Any]]) -> FakeRedisPubSubClient:
        return FakeRedisPubSubClient(messages)

    return _make
