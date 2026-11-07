"""CORS: whitelist origin и отказ чужому Origin."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from starlette.testclient import TestClient


def test_cors_preflight_allows_whitelisted_origin(monkeypatch: pytest.MonkeyPatch) -> None:
    s = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        admin_session_secret="x" * 32,
        cors_origins="https://portal.example",
        document_trash_purge_enabled=False,
    )
    monkeypatch.setattr("app.main.get_settings", lambda: s)
    from app.main import create_app

    application = create_app()
    with TestClient(application) as client:
        allowed = client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://portal.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert allowed.headers.get("access-control-allow-origin") == "https://portal.example"
        assert allowed.headers.get("access-control-allow-credentials") == "true"

        denied = client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert denied.headers.get("access-control-allow-origin") != "https://evil.example"
