"""Тесты create_app и вспомогательных функций main."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
from app.core.config import Settings
from app.main import _mask_url_password, create_app


def test_mask_url_password_redacts_on_parse_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def broken_parse(_url: str) -> SimpleNamespace:
        raise ValueError("bad url")

    monkeypatch.setattr("app.main.urlparse", broken_parse)
    url = "redis://user:pass@host:6379/0"
    assert _mask_url_password(url) == "***"


def test_mask_url_password_password_only_netloc() -> None:
    parsed = urlparse("redis://:secret@host:6379/0")
    assert parsed.password == "secret"
    masked = _mask_url_password("redis://:secret@host:6379/0")
    assert "secret" not in masked
    assert ":***@host:6379" in masked


def test_create_app_raises_without_admin_secret_outside_testing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        admin_session_secret="",
        debug=False,
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)
    monkeypatch.delenv("TESTING", raising=False)

    with pytest.raises(RuntimeError, match="ADMIN_SESSION_SECRET"):
        create_app()


def test_create_app_uses_ephemeral_secret_in_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        admin_session_secret="",
        debug=True,
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)
    application = create_app()
    assert application.title == s.app_name
    assert s.admin_session_secret  # эфемерный секрет записан в Settings для HMAC photo


def test_create_app_rejects_insecure_minio_outside_debug(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        admin_session_secret="x" * 32,
        debug=False,
        minio_access_key="minioadmin",
        minio_secret_key="minioadmin",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)
    monkeypatch.delitem(sys.modules, "pytest", raising=False)
    monkeypatch.delenv("TESTING", raising=False)

    with pytest.raises(RuntimeError, match="MINIO_"):
        create_app()


def test_create_app_includes_telegram_webhook_router(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        admin_session_secret="x" * 32,
        telegram_bot_token="123456:ABC-DEF",
        telegram_use_polling=False,
        telegram_webhook_path="/tg/webhook",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)
    monkeypatch.setattr("app.portal_telegram.webhook.get_settings", lambda: s)
    application = create_app()

    # Не смотрим внутренности FastAPI (_IncludedRouter и т.п.) — проверяем маршрут по ответу.
    # Без секрета вебхук отвечает 403, а не 404.
    from starlette.testclient import TestClient

    with TestClient(application) as client:
        response = client.post("/tg/webhook", content=b"{}")
    assert response.status_code == 403


def test_create_app_skips_telegram_webhook_when_polling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        admin_session_secret="x" * 32,
        telegram_bot_token="123456:ABC-DEF",
        telegram_use_polling=True,
        telegram_webhook_path="/tg/webhook",
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)
    monkeypatch.setattr("app.core.config.get_settings", lambda: s)
    monkeypatch.setattr("app.portal_telegram.webhook.get_settings", lambda: s)
    application = create_app()

    from starlette.testclient import TestClient

    with TestClient(application) as client:
        response = client.post("/tg/webhook", content=b"{}")
    assert response.status_code == 404
