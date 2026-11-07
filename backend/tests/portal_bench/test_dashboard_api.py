"""HTTP-контракт дашборда бенч: 401/403 и чтение снимка админом."""

from __future__ import annotations

import pytest
from app.infrastructure.db.models.portal_bench import PortalBenchYearSnapshot
from app.portal_bench.services._snapshot import upsert_year_snapshot
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from tests.portal_bench.conftest import BENCH_DASHBOARD_API, assert_api_error


async def test_dashboard_requires_auth(client_sqlite_only: AsyncClient) -> None:
    r = await client_sqlite_only.get(BENCH_DASHBOARD_API)
    assert_api_error(r, 401, "unauthorized")


async def test_dashboard_forbidden_without_manager_role(client_no_idp: AsyncClient) -> None:
    r = await client_no_idp.get(BENCH_DASHBOARD_API)
    assert_api_error(r, 403, "forbidden")


async def test_dashboard_forbidden_for_timesheet_only(client_developer: AsyncClient) -> None:
    r = await client_developer.get(BENCH_DASHBOARD_API)
    assert_api_error(r, 403, "forbidden")


async def test_dashboard_ok_for_manager(client_manager: AsyncClient) -> None:
    r = await client_manager.get(BENCH_DASHBOARD_API)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "cards" in body
    assert isinstance(body["specialization_stats"], list)


async def test_dashboard_admin_seeds_2025_and_returns_cards(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    r = await client_admin.get(BENCH_DASHBOARD_API)
    assert r.status_code == 200, r.text
    body = r.json()
    assert 2025 in body["years"]
    assert 2026 in body["years"]
    assert body["cards"]["avg_rate"] is not None
    assert body["cards"]["offers"] >= 0
    assert isinstance(body["specialization_stats"], list)
    assert isinstance(body["monthly_dynamics"], list)
    assert body["is_stale"] is False
    assert body["stale_message"] is None
    assert "last_success_at" in body

    seeded = await sqlite_session.get(PortalBenchYearSnapshot, 2025)
    assert seeded is not None
    assert seeded.frozen is True
    assert seeded.source == "seed"
    assert len(seeded.records) > 0
    live = await sqlite_session.get(PortalBenchYearSnapshot, 2026)
    assert live is not None
    assert live.frozen is False

    again = await client_admin.get(BENCH_DASHBOARD_API)
    assert again.status_code == 200
    rows = (await sqlite_session.execute(select(PortalBenchYearSnapshot))).scalars().all()
    assert {row.year for row in rows} == {2025, 2026}
    assert "DA" in body["specializations"]
    assert any(row["specialization"] == "DA" for row in body["specialization_stats"])


async def test_dashboard_stale_when_google_sheets_enabled(
    client_admin: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.config import Settings

    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        google_sheets_sync_enabled=True,
        google_sheets_spreadsheet_id="sheet-id-1",
        google_sheets_service_account_json='{"client_email":"a@b","private_key":"k"}',
    )
    monkeypatch.setattr("app.portal_bench.services._snapshot.get_settings", lambda: settings)
    r = await client_admin.get(BENCH_DASHBOARD_API)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_stale"] is True
    assert "не свежие" in (body["stale_message"] or "").lower()


async def test_dashboard_rejects_partial_date_range(client_admin: AsyncClient) -> None:
    r = await client_admin.get(BENCH_DASHBOARD_API, params={"date_from": "2026-01-01"})
    assert_api_error(r, 422, "validation_error")


async def test_dashboard_filter_year_keeps_full_year_catalog(client_admin: AsyncClient) -> None:
    r = await client_admin.get(BENCH_DASHBOARD_API, params={"year": 2025})
    assert r.status_code == 200, r.text
    body = r.json()
    assert 2025 in body["years"]
    assert 2026 in body["years"]
    assert body["monthly_summary"]["years"] == [2025]


async def test_dashboard_filter_specialization_keeps_full_spec_catalog(
    client_admin: AsyncClient,
) -> None:
    unfiltered = await client_admin.get(BENCH_DASHBOARD_API)
    assert unfiltered.status_code == 200, unfiltered.text
    all_specs = unfiltered.json()["specializations"]
    assert len(all_specs) >= 2
    chosen = all_specs[0]
    r = await client_admin.get(BENCH_DASHBOARD_API, params={"specialization": chosen})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["specializations"]) == set(all_specs)


async def test_dashboard_filter_multiple_specializations(client_admin: AsyncClient) -> None:
    unfiltered = await client_admin.get(BENCH_DASHBOARD_API)
    assert unfiltered.status_code == 200, unfiltered.text
    all_specs = unfiltered.json()["specializations"]
    assert len(all_specs) >= 2
    first, second = all_specs[0], all_specs[1]
    first_only = await client_admin.get(BENCH_DASHBOARD_API, params={"specialization": first})
    second_only = await client_admin.get(BENCH_DASHBOARD_API, params={"specialization": second})
    assert first_only.status_code == 200, first_only.text
    assert second_only.status_code == 200, second_only.text
    r = await client_admin.get(
        BENCH_DASHBOARD_API,
        params=[("specialization", first), ("specialization", second)],
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body["specializations"]) == set(all_specs)
    shown = {row["specialization"] for row in body["specialization_stats"]}
    assert shown <= {first, second}
    first_offers = first_only.json()["cards"]["offers"]
    second_offers = second_only.json()["cards"]["offers"]
    assert body["cards"]["offers"] == first_offers + second_offers
    if first_offers:
        assert first in shown
    if second_offers:
        assert second in shown


async def test_dashboard_reclassifies_da_rows_in_filter_and_stats(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """ФИО из сводной с устаревшей меткой SA/Other всё равно дают DA в каталоге и графиках."""
    await upsert_year_snapshot(
        sqlite_session,
        year=2026,
        records=[
            {
                "year": 2026,
                "month": "Январь",
                "month_num": 1,
                "developer": "Хватов Виктор DA",
                "specialization": "Other",
                "cv_sent": 9,
                "offer": 1,
                "project_start": 0,
                "rejection": 0,
            },
            {
                "year": 2026,
                "month": "Июль",
                "month_num": 7,
                "developer": "Александр Анфимов DA",
                "specialization": "SA",
                "cv_sent": 1,
                "offer": 0,
                "project_start": 1,
                "rejection": 0,
            },
        ],
        source="sheets",
        frozen=False,
    )
    r = await client_admin.get(BENCH_DASHBOARD_API, params={"year": 2026})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "DA" in body["specializations"]
    by_spec = {row["specialization"]: row for row in body["specialization_stats"]}
    assert "DA" in by_spec
    assert by_spec["DA"]["cv_sent"] == 10
    assert by_spec["DA"]["offers"] == 1
    assert by_spec["DA"]["project_starts"] == 1
    assert "SA" not in by_spec
    assert "Other" not in by_spec


async def test_dashboard_admin_filter_unknown_year_empty_cards(client_admin: AsyncClient) -> None:
    r = await client_admin.get(BENCH_DASHBOARD_API, params={"year": 2099})
    assert r.status_code == 200, r.text
    body = r.json()
    assert 2025 in body["years"]
    assert 2026 in body["years"]
    assert body["cards"]["avg_rate"] is None
    assert body["cards"]["offers"] == 0
