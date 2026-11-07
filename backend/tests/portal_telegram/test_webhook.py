"""Webhook входящих обновлений Telegram (отдельный роутер)."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.api.exception_handlers import register_exception_handlers
from app.portal_telegram.webhook import build_telegram_webhook_router
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from tests.conftest import make_oidc_settings


def _secret_from_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def _build_test_app() -> FastAPI:
    """Роутер вебхука + обработчики ошибок — как в main.py (AppError → JSON)."""
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(build_telegram_webhook_router())
    return app


@pytest.fixture
def patch_webhook_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    s = make_oidc_settings(
        telegram_bot_token="123:SECRETTOKEN",
        telegram_webhook_path="tg/incoming",
        telegram_webhook_secret="explicit-secret",
    )
    monkeypatch.setattr("app.portal_telegram.webhook.get_settings", lambda: s)


@pytest.mark.asyncio
async def test_webhook_normalizes_path_without_leading_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    s = make_oidc_settings(
        telegram_bot_token="1:x",
        telegram_webhook_path="no-leading-slash",
        telegram_webhook_secret="s",
    )
    monkeypatch.setattr("app.portal_telegram.webhook.get_settings", lambda: s)
    dp = MagicMock()
    dp.feed_update = AsyncMock()
    monkeypatch.setattr("app.portal_telegram.bot.instance.get_dispatcher", lambda: dp)
    monkeypatch.setattr("app.portal_telegram.bot.instance.get_bot", lambda: MagicMock())
    app = _build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/no-leading-slash",
            content=b'{"update_id":1}',
            headers={"X-Telegram-Bot-Api-Secret-Token": "s"},
        )
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_webhook_403_on_wrong_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    s = make_oidc_settings(
        telegram_bot_token="1:x",
        telegram_webhook_path="/hook",
        telegram_webhook_secret="good",
    )
    monkeypatch.setattr("app.portal_telegram.webhook.get_settings", lambda: s)
    app = _build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/hook", content=b"{}", headers={"X-Telegram-Bot-Api-Secret-Token": "bad"})
        assert res.status_code == 403
        assert res.json()["code"] == "forbidden"


@pytest.mark.asyncio
async def test_webhook_403_on_secret_length_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    """Разная длина секрета — 403, не 500 от hmac.compare_digest (hmac_secrets_equal)."""
    s = make_oidc_settings(
        telegram_bot_token="1:x",
        telegram_webhook_path="/hook",
        telegram_webhook_secret="expected-secret-value",
    )
    monkeypatch.setattr("app.portal_telegram.webhook.get_settings", lambda: s)
    app = _build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/hook", content=b"{}", headers={"X-Telegram-Bot-Api-Secret-Token": "short"})
        assert res.status_code == 403
        assert res.json()["code"] == "forbidden"


@pytest.mark.asyncio
async def test_webhook_403_on_missing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    s = make_oidc_settings(
        telegram_bot_token="1:x",
        telegram_webhook_path="/hook",
        telegram_webhook_secret="need-this",
    )
    monkeypatch.setattr("app.portal_telegram.webhook.get_settings", lambda: s)
    app = _build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/hook", content=b'{"update_id":1}')
        assert res.status_code == 403
        assert res.json()["code"] == "forbidden"


@pytest.mark.asyncio
async def test_webhook_uses_explicit_secret(patch_webhook_settings: None, monkeypatch: pytest.MonkeyPatch) -> None:
    dp = MagicMock()
    dp.feed_update = AsyncMock()
    monkeypatch.setattr("app.portal_telegram.bot.instance.get_dispatcher", lambda: dp)
    monkeypatch.setattr("app.portal_telegram.bot.instance.get_bot", lambda: MagicMock())

    app = _build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/tg/incoming",
            content=b'{"update_id":42}',
            headers={"X-Telegram-Bot-Api-Secret-Token": "explicit-secret"},
        )
        assert res.status_code == 200
        dp.feed_update.assert_awaited_once()


@pytest.mark.asyncio
async def test_webhook_uses_token_derived_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    token = "999:ABC"
    s = make_oidc_settings(
        telegram_bot_token=token,
        telegram_webhook_path="/wh",
        telegram_webhook_secret="",
    )
    monkeypatch.setattr("app.portal_telegram.webhook.get_settings", lambda: s)
    dp = MagicMock()
    dp.feed_update = AsyncMock()
    monkeypatch.setattr("app.portal_telegram.bot.instance.get_dispatcher", lambda: dp)
    monkeypatch.setattr("app.portal_telegram.bot.instance.get_bot", lambda: MagicMock())

    app = _build_test_app()
    hdr = _secret_from_token(token)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/wh",
            content=b'{"update_id":1}',
            headers={"X-Telegram-Bot-Api-Secret-Token": hdr},
        )
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_webhook_400_on_bad_json(monkeypatch: pytest.MonkeyPatch) -> None:
    s = make_oidc_settings(
        telegram_bot_token="1:x",
        telegram_webhook_path="/hook",
        telegram_webhook_secret="sec",
    )
    monkeypatch.setattr("app.portal_telegram.webhook.get_settings", lambda: s)
    app = _build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/hook", content=b"not-json", headers={"X-Telegram-Bot-Api-Secret-Token": "sec"})
        assert res.status_code == 400
        assert res.json()["code"] == "bad_request"


@pytest.mark.asyncio
async def test_webhook_200_feeds_update(monkeypatch: pytest.MonkeyPatch) -> None:
    s = make_oidc_settings(
        telegram_bot_token="1:x",
        telegram_webhook_path="/hook",
        telegram_webhook_secret="sec",
    )
    monkeypatch.setattr("app.portal_telegram.webhook.get_settings", lambda: s)
    dp = MagicMock()
    dp.feed_update = AsyncMock()
    bot_mock = MagicMock()
    monkeypatch.setattr("app.portal_telegram.bot.instance.get_dispatcher", lambda: dp)
    monkeypatch.setattr("app.portal_telegram.bot.instance.get_bot", lambda: bot_mock)

    app = _build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/hook",
            content=b'{"update_id":100}',
            headers={"X-Telegram-Bot-Api-Secret-Token": "sec"},
        )
        assert res.status_code == 200
        assert res.text == "OK"
        dp.feed_update.assert_awaited_once()
        args = dp.feed_update.await_args[0]
        assert args[0] is bot_mock
        assert args[1].update_id == 100


@pytest.mark.asyncio
async def test_webhook_200_when_feed_update_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    s = make_oidc_settings(
        telegram_bot_token="1:x",
        telegram_webhook_path="/hook",
        telegram_webhook_secret="sec",
    )
    monkeypatch.setattr("app.portal_telegram.webhook.get_settings", lambda: s)
    dp = MagicMock()
    dp.feed_update = AsyncMock(side_effect=RuntimeError("handler boom"))
    monkeypatch.setattr("app.portal_telegram.bot.instance.get_dispatcher", lambda: dp)
    monkeypatch.setattr("app.portal_telegram.bot.instance.get_bot", lambda: MagicMock())

    app = _build_test_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/hook",
            content=b'{"update_id":100}',
            headers={"X-Telegram-Bot-Api-Secret-Token": "sec"},
        )
        assert res.status_code == 200
        assert res.text == "OK"
