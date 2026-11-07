"""Sync Google → снимок: живой год пишется, frozen 2025 и старый снимок не чистятся."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.core.config import Settings
from app.core.exceptions import ServiceUnavailableError
from app.infrastructure.db.models.portal_bench import PortalBenchSyncState, PortalBenchYearSnapshot
from app.portal_bench.constants import SYNC_STATE_ID
from app.portal_bench.services._snapshot import (
    ensure_snapshots_and_load_records,
    load_dashboard,
    upsert_year_snapshot,
)
from app.portal_bench.services._sync import sync_bench_from_sheets
from sqlalchemy.ext.asyncio import AsyncSession


def _settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        google_sheets_sync_enabled=True,
        google_sheets_spreadsheet_id="sheet-id-1",
        google_sheets_service_account_json='{"client_email":"x@y","private_key":"k"}',
    )


@pytest.mark.asyncio
async def test_sync_writes_2026_keeps_frozen_2025(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await ensure_snapshots_and_load_records(sqlite_session)
    frozen_len = len((await sqlite_session.get(PortalBenchYearSnapshot, 2025)).records)  # type: ignore[union-attr]

    async def fake_fetch(_self: object) -> dict[str, list[list[object]]]:
        return {
            "ОБЩИЙ СТАТУС ПО ЗАПРОСАМ": [[None, 2026], ["Разработчик", "Ставка"], ["Петров iOS", 2100]],
            "Январь сводная": [
                ["шапка"],
                ["шапка2"],
                ["Петров iOS", 3, 0, 0, 0, 0, 0, 0, 1, 1, "выход 10.01"],
            ],
        }

    monkeypatch.setattr(
        "app.portal_bench.services._sync.GoogleSheetsClient.fetch_dashboard_sheets",
        fake_fetch,
    )
    ok = await sync_bench_from_sheets(sqlite_session, _settings(), AsyncMock())
    assert ok is True
    live = await sqlite_session.get(PortalBenchYearSnapshot, 2026)
    assert live is not None
    assert live.frozen is False
    assert any(r.get("developer") == "Петров iOS" for r in live.records)
    frozen = await sqlite_session.get(PortalBenchYearSnapshot, 2025)
    assert frozen is not None
    assert frozen.frozen is True
    assert len(frozen.records) == frozen_len
    state = await sqlite_session.get(PortalBenchSyncState, SYNC_STATE_ID)
    assert state is not None
    assert state.last_success_at is not None
    assert state.last_error is None


@pytest.mark.asyncio
async def test_sync_google_error_keeps_existing_snapshot(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await upsert_year_snapshot(
        sqlite_session,
        year=2026,
        records=[{"year": 2026, "developer": "Старый"}],
        source="sheets",
        frozen=False,
    )

    async def boom(_self: object) -> dict[str, list[list[object]]]:
        raise ServiceUnavailableError("Google Sheets временно недоступна")

    monkeypatch.setattr(
        "app.portal_bench.services._sync.GoogleSheetsClient.fetch_dashboard_sheets",
        boom,
    )
    ok = await sync_bench_from_sheets(sqlite_session, _settings(), AsyncMock())
    assert ok is False
    live = await sqlite_session.get(PortalBenchYearSnapshot, 2026)
    assert live is not None
    assert live.records[0]["developer"] == "Старый"
    state = await sqlite_session.get(PortalBenchSyncState, SYNC_STATE_ID)
    assert state is not None
    assert state.last_error == "Google Sheets недоступна"
    assert state.last_success_at is None


@pytest.mark.asyncio
async def test_sync_replaces_stale_2026_and_dashboard_shows_da(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await upsert_year_snapshot(
        sqlite_session,
        year=2026,
        records=[{"year": 2026, "developer": "Старый без DA", "specialization": "iOS", "cv_sent": 1}],
        source="sheets",
        frozen=False,
    )

    async def fake_fetch(_self: object) -> dict[str, list[list[object]]]:
        return {
            "ОБЩИЙ СТАТУС ПО ЗАПРОСАМ": [[None, 2026]],
            "Январь сводная": [
                ["шапка"],
                ["шапка2"],
                ["Хватов Виктор DA", 9, 0, 0, 0, 0, 0, 0, 1, 0, ""],
            ],
            "Июль сводная": [
                ["шапка"],
                ["шапка2"],
                ["Александр Анфимов DA", 1, 0, 0, 0, 0, 0, 0, 0, 1, ""],
            ],
        }

    monkeypatch.setattr(
        "app.portal_bench.services._sync.GoogleSheetsClient.fetch_dashboard_sheets",
        fake_fetch,
    )
    ok = await sync_bench_from_sheets(sqlite_session, _settings(), AsyncMock())
    assert ok is True
    live = await sqlite_session.get(PortalBenchYearSnapshot, 2026)
    assert live is not None
    names = {str(row.get("developer")) for row in live.records}
    assert "Хватов Виктор DA" in names
    assert "Александр Анфимов DA" in names
    assert "Старый без DA" not in names

    dash = await load_dashboard(sqlite_session, year=2026)
    assert "DA" in dash["specializations"]
    by_spec = {row["specialization"]: row for row in dash["specialization_stats"]}
    assert by_spec["DA"]["cv_sent"] == 10
    assert by_spec["DA"]["offers"] == 1
    assert by_spec["DA"]["project_starts"] == 1
