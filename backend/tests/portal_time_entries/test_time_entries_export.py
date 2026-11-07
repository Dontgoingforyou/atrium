"""Тесты выгрузки таймшитов: RBAC, форматы ответа, содержимое CSV."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from unittest.mock import patch

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.infrastructure.db.models.portal_time_entry import PortalTimeEntry
from app.main import app
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin
from tests.portal_time_entries.conftest import TIME_ENTRIES_API, assert_api_error, assert_pydantic_422


@pytest.mark.asyncio
async def test_export_csv_admin_contains_seeded_rows(client_admin_entries: AsyncClient) -> None:
    r = await client_admin_entries.get(
        f"{TIME_ENTRIES_API}/export",
        params={"format": "csv", "month": "2026-04", "user_sub": "manager-sub"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers.get("content-disposition", "")
    body = r.text
    assert "2026-04-01" in body
    assert "2026-04-15" in body
    assert "Задача A" in body
    assert ",120," in body or ",120.0," in body
    assert ",90," in body or ",90.0," in body


@pytest.mark.asyncio
async def test_export_xlsx_admin_success(client_admin_entries: AsyncClient) -> None:
    pytest.importorskip("openpyxl", reason="openpyxl не установлен")
    r = await client_admin_entries.get(
        f"{TIME_ENTRIES_API}/export",
        params={"format": "xlsx", "month": "2026-04", "user_sub": "manager-sub"},
    )
    assert r.status_code == 200, r.text
    ct = r.headers["content-type"]
    assert "spreadsheet" in ct or "xlsx" in ct or "openxmlformats" in ct
    assert "attachment" in r.headers.get("content-disposition", "")
    assert len(r.content) > 0


@pytest.mark.asyncio
async def test_export_pdf_admin_success(client_admin_entries: AsyncClient) -> None:
    pytest.importorskip("reportlab", reason="reportlab не установлен")
    r = await client_admin_entries.get(
        f"{TIME_ENTRIES_API}/export",
        params={"format": "pdf", "month": "2026-04", "user_sub": "manager-sub"},
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert "attachment" in r.headers.get("content-disposition", "")
    assert len(r.content) > 0


@pytest.mark.asyncio
async def test_export_manager_own_entries_only(client_manager_entries: AsyncClient) -> None:
    """Менеджер без user_sub выгружает только свои записи."""
    r = await client_manager_entries.get(
        f"{TIME_ENTRIES_API}/export",
        params={"format": "csv", "month": "2026-04"},
    )
    assert r.status_code == 200, r.text
    body = r.text
    assert "manager-sub" not in body  # sub не попадает в CSV
    assert "2026-04-01" in body
    assert "2026-04-15" in body
    assert "2026-04-03" not in body  # запись user-sub за тот же месяц


@pytest.mark.asyncio
async def test_export_manager_can_export_colleague(client_manager_entries: AsyncClient) -> None:
    r = await client_manager_entries.get(
        f"{TIME_ENTRIES_API}/export",
        params={"format": "csv", "month": "2026-04", "user_sub": "user-sub"},
    )
    assert r.status_code == 200, r.text
    assert "2026-04-03" in r.text
    assert "Разработка" in r.text


@pytest.mark.asyncio
async def test_export_admin_without_user_sub_includes_all_users(
    client_admin_entries: AsyncClient,
) -> None:
    r = await client_admin_entries.get(
        f"{TIME_ENTRIES_API}/export",
        params={"format": "csv", "month": "2026-04"},
    )
    assert r.status_code == 200, r.text
    body = r.text
    assert "2026-04-01" in body
    assert "2026-04-03" in body
    assert "Задача A" in body
    assert "Разработка" in body


@pytest.mark.asyncio
async def test_export_developer_own_entries(client_developer_entries: AsyncClient) -> None:
    r = await client_developer_entries.get(
        f"{TIME_ENTRIES_API}/export",
        params={"format": "csv", "month": "2026-04"},
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_export_developer_forbidden_for_other_user(
    client_developer_entries: AsyncClient,
) -> None:
    r = await client_developer_entries.get(
        f"{TIME_ENTRIES_API}/export",
        params={"format": "csv", "month": "2026-04", "user_sub": "manager-sub"},
    )
    assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_export_missing_month_returns_422(client_admin_entries: AsyncClient) -> None:
    r = await client_admin_entries.get(
        f"{TIME_ENTRIES_API}/export",
        params={"format": "csv"},
    )
    assert_pydantic_422(r)


@pytest.mark.asyncio
async def test_export_invalid_format_returns_422(client_admin_entries: AsyncClient) -> None:
    r = await client_admin_entries.get(
        f"{TIME_ENTRIES_API}/export",
        params={"format": "docx", "month": "2026-04"},
    )
    assert_pydantic_422(r)


@pytest.mark.asyncio
async def test_export_content_disposition_filename(client_admin_entries: AsyncClient) -> None:
    r = await client_admin_entries.get(
        f"{TIME_ENTRIES_API}/export",
        params={"format": "csv", "month": "2026-04", "user_sub": "manager-sub"},
    )
    assert r.status_code == 200, r.text
    cd = r.headers.get("content-disposition", "")
    assert "filename=" in cd
    assert "2026-04" in cd


@pytest.mark.asyncio
async def test_export_csv_sanitizes_formula_cells(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    sqlite_session.add(
        PortalTimeEntry(
            user_sub="admin-sub",
            worked_on=date(2026, 4, 10),
            minutes=30,
            task_name='=HYPERLINK("http://evil")',
            note="=1+1",
        )
    )
    await sqlite_session.commit()

    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    prev_db = app.dependency_overrides.get(get_db_session)
    prev_user = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            r = await ac.get(
                f"{TIME_ENTRIES_API}/export",
                params={"format": "csv", "month": "2026-04", "user_sub": "admin-sub"},
            )
            assert r.status_code == 200, r.text
            assert "=HYPERLINK" in r.text
            assert "'=HYPERLINK" in r.text
            assert "'=1+1" in r.text
    finally:
        if prev_db is not None:
            app.dependency_overrides[get_db_session] = prev_db
        else:
            app.dependency_overrides.pop(get_db_session, None)
        if prev_user is not None:
            app.dependency_overrides[get_current_user] = prev_user
        else:
            app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_export_rejects_when_over_cap(
    client_admin_entries: AsyncClient,
) -> None:
    with patch("app.portal_time_entries.services._export._EXPORT_ENTRY_LIMIT", 2):
        r = await client_admin_entries.get(
            f"{TIME_ENTRIES_API}/export",
            params={"format": "csv", "month": "2026-04"},
        )
    assert_api_error(r, 422, "validation_error")
