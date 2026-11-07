"""HTTP-контракт выгрузки дашборда бенч: 401/403 и файлы csv/xlsx."""

from __future__ import annotations

import pytest
from app.portal_bench.services._snapshot import upsert_year_snapshot
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.portal_bench.conftest import BENCH_DASHBOARD_API, BENCH_EXPORT_API, assert_api_error


async def test_export_requires_auth(client_sqlite_only: AsyncClient) -> None:
    r = await client_sqlite_only.get(BENCH_EXPORT_API, params={"format": "csv"})
    assert_api_error(r, 401, "unauthorized")


async def test_export_forbidden_without_manager_role(client_no_idp: AsyncClient) -> None:
    r = await client_no_idp.get(BENCH_EXPORT_API, params={"format": "csv"})
    assert_api_error(r, 403, "forbidden")


async def test_export_forbidden_for_timesheet_only(client_developer: AsyncClient) -> None:
    r = await client_developer.get(BENCH_EXPORT_API, params={"format": "xlsx"})
    assert_api_error(r, 403, "forbidden")


async def test_export_ok_for_manager(client_manager: AsyncClient) -> None:
    r = await client_manager.get(BENCH_EXPORT_API, params={"format": "csv", "year": 2025})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")


async def test_export_rejects_partial_date_range(client_admin: AsyncClient) -> None:
    r = await client_admin.get(BENCH_EXPORT_API, params={"format": "csv", "date_to": "2026-01-31"})
    assert_api_error(r, 422, "validation_error")


async def test_export_csv_multiple_specializations(client_admin: AsyncClient) -> None:
    dash = await client_admin.get(BENCH_DASHBOARD_API)
    assert dash.status_code == 200, dash.text
    specs = dash.json()["specializations"]
    assert "iOS" in specs and "Android" in specs
    r = await client_admin.get(
        BENCH_EXPORT_API,
        params=[("format", "csv"), ("specialization", "iOS"), ("specialization", "Android")],
    )
    assert r.status_code == 200, r.text
    body = r.text
    assert "iOS" in body
    assert "Android" in body
    only_ios = await client_admin.get(
        BENCH_EXPORT_API,
        params={"format": "csv", "specialization": "iOS"},
    )
    assert only_ios.status_code == 200, only_ios.text
    assert "iOS" in only_ios.text


async def test_export_csv_admin_contains_2025_slice(client_admin: AsyncClient) -> None:
    r = await client_admin.get(BENCH_EXPORT_API, params={"format": "csv", "year": 2025})
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    body = r.text
    assert "Специализация" in body
    assert "iOS" in body


async def test_export_xlsx_admin_success(client_admin: AsyncClient) -> None:
    pytest.importorskip("openpyxl", reason="openpyxl не установлен")
    r = await client_admin.get(BENCH_EXPORT_API, params={"format": "xlsx"})
    assert r.status_code == 200, r.text
    assert "spreadsheet" in r.headers["content-type"] or "openxmlformats" in r.headers["content-type"]
    assert "attachment" in r.headers.get("content-disposition", "")
    assert len(r.content) > 0


async def test_export_csv_sanitizes_formula_cells(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    await upsert_year_snapshot(
        sqlite_session,
        year=2026,
        records=[
            {
                "year": 2026,
                "month": "Январь",
                "month_num": 1,
                "developer": "=CMD|'/C calc'!A0",
                "specialization": "iOS",
                "cv_sent": 1,
                "screening": 0,
                "internal_interview": 0,
                "tech_stage_1": 0,
                "final_stage": 0,
                "osup": 0,
                "rejection": 0,
                "offer": 0,
                "project_start": 0,
                "comment": "+1-555",
                "rate": 2000,
                "start_date": None,
                "request_date": "01.01.2026",
            }
        ],
        source="sheets",
        frozen=False,
    )
    r = await client_admin.get(BENCH_EXPORT_API, params={"format": "csv", "year": 2026})
    assert r.status_code == 200, r.text
    assert "'=CMD" in r.text
    assert "'+1-555" in r.text
