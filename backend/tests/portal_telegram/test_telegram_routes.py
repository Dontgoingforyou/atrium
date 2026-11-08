"""HTTP-эндпоинты привязки Telegram: happy-path и 503."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.infrastructure.db.models.portal_telegram_binding import PortalTelegramBinding
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.conftest import make_oidc_settings
from tests.portal_telegram.conftest import TELEGRAM_BIND_API, assert_api_error


@pytest.mark.asyncio
async def test_bind_init_returns_code_and_url(
    client_user: AsyncClient,
    patch_telegram_bind_env: None,
) -> None:
    res = await client_user.post(f"{TELEGRAM_BIND_API}/init")
    assert res.status_code == 200
    data = res.json()
    assert "code" in data and data["code"].startswith("tgb_")
    assert data["bot_url"].startswith("https://t.me/AtriumTestBot?start=")


@pytest.mark.asyncio
async def test_bind_status_not_bound(client_user: AsyncClient) -> None:
    res = await client_user.get(f"{TELEGRAM_BIND_API}/status")
    assert res.status_code == 200
    assert res.json() == {"bound": False, "created_at": None}


@pytest.mark.asyncio
async def test_bind_status_bound(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=1))
    await sqlite_session.commit()
    res = await client_user.get(f"{TELEGRAM_BIND_API}/status")
    assert res.status_code == 200
    body = res.json()
    assert body["bound"] is True
    assert body["created_at"] is not None


@pytest.mark.asyncio
async def test_bind_init_503_without_redis(monkeypatch: pytest.MonkeyPatch, client_user: AsyncClient) -> None:
    monkeypatch.setattr("app.portal_telegram.routes.telegram.get_redis_client", lambda: None)
    monkeypatch.setattr("app.portal_telegram.routes.telegram.get_bot_username", lambda: "Bot")
    monkeypatch.setattr(
        "app.portal_telegram.routes.telegram.get_settings",
        lambda: make_oidc_settings(telegram_bot_token="1:x"),
    )
    res = await client_user.post(f"{TELEGRAM_BIND_API}/init")
    assert_api_error(res, 503, "service_unavailable")


@pytest.mark.asyncio
async def test_bind_init_503_without_bot_token(monkeypatch: pytest.MonkeyPatch, client_user: AsyncClient) -> None:
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=None)
    fake_redis.set = AsyncMock(return_value=True)
    monkeypatch.setattr("app.portal_telegram.routes.telegram.get_redis_client", lambda: fake_redis)
    monkeypatch.setattr("app.portal_telegram.routes.telegram.get_bot_username", lambda: "Bot")
    monkeypatch.setattr(
        "app.portal_telegram.routes.telegram.get_settings",
        lambda: make_oidc_settings(telegram_bot_token=""),
    )
    res = await client_user.post(f"{TELEGRAM_BIND_API}/init")
    assert_api_error(res, 503, "service_unavailable")


@pytest.mark.asyncio
async def test_bind_init_503_without_username(monkeypatch: pytest.MonkeyPatch, client_user: AsyncClient) -> None:
    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=None)
    fake_redis.set = AsyncMock(return_value=True)
    monkeypatch.setattr("app.portal_telegram.routes.telegram.get_redis_client", lambda: fake_redis)
    monkeypatch.setattr("app.portal_telegram.routes.telegram.get_bot_username", lambda: "")
    monkeypatch.setattr(
        "app.portal_telegram.routes.telegram.get_settings",
        lambda: make_oidc_settings(telegram_bot_token="1:x"),
    )
    res = await client_user.post(f"{TELEGRAM_BIND_API}/init")
    assert_api_error(res, 503, "service_unavailable")


@pytest.mark.asyncio
async def test_delete_bind_returns_204(client_user: AsyncClient, sqlite_session: AsyncSession) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=7))
    await sqlite_session.commit()
    res = await client_user.delete(TELEGRAM_BIND_API)
    assert res.status_code == 204

    row = await sqlite_session.scalar(select(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == "user-sub"))
    assert row is None


@pytest.mark.asyncio
async def test_delete_bind_idempotent_when_not_bound(client_user: AsyncClient, sqlite_session: AsyncSession) -> None:
    res = await client_user.delete(TELEGRAM_BIND_API)
    assert res.status_code == 204
    n = await sqlite_session.scalar(select(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == "user-sub"))
    assert n is None
