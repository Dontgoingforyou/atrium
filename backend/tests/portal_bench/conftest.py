"""Фикстуры HTTP-тестов дашборда бенч."""

from __future__ import annotations

import pytest
from app.core.config import Settings
from httpx import Response

BENCH_DASHBOARD_API = "/api/v1/portal/bench/dashboard"
BENCH_EXPORT_API = "/api/v1/portal/bench/export"


@pytest.fixture(autouse=True)
def disable_google_sheets_for_bench_tests(monkeypatch: pytest.MonkeyPatch) -> None:
    """CI подставляет GOOGLE_SHEETS_* из Variables — unit-тесты не должны от этого зависеть."""
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        google_sheets_sync_enabled=False,
        google_sheets_service_account_json="",
    )
    monkeypatch.setattr("app.portal_bench.services._snapshot.get_settings", lambda: settings)


def assert_api_error(response: Response, status: int, code: str) -> None:
    """Ошибка AppError: и HTTP-статус, и контрактный `code`."""
    assert response.status_code == status, response.text
    assert response.json()["code"] == code
