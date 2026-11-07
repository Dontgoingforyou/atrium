"""Тесты импорта таймшитов из CSV: POST /portal/time-entries/import-jira-csv."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from tests.portal_time_entries.conftest import TIME_ENTRIES_API, assert_api_error

_HEADER = '"Ключ задачи","Тема задачи","Часов","Дата работы","Имя пользователя"\n'


def _csv_bytes(rows: str) -> bytes:
    return (_HEADER + rows).encode("utf-8")


def _files(content: bytes, *, filename: str = "worklog.csv", content_type: str = "text/csv") -> dict:
    return {"file": (filename, content, content_type)}


@pytest.mark.asyncio
async def test_import_creates_entries_from_valid_csv(
    client_regular_entries: AsyncClient,
) -> None:
    content = _csv_bytes(
        '"STLT-1","Сделать штуку","0.5","2026-07-01 08:43","ee.nikolaev"\n'
        '"STLT-2","Административные задачи","1.5","2026-07-02 16:34","ee.nikolaev"\n'
    )
    r = await client_regular_entries.post(
        f"{TIME_ENTRIES_API}/import-jira-csv",
        files=_files(content),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["created_count"] == 2
    assert body["skipped_count"] == 0
    assert body["errors"] == []
    assert {row["task_name"] for row in body["created"]} == {"Сделать штуку", "Административные задачи"}
    assert all(row["user_sub"] == "user-sub" for row in body["created"])
    assert all(row["task_id"] is None for row in body["created"])

    listed = await client_regular_entries.get(
        TIME_ENTRIES_API,
        params={"date_from": "2026-07-01", "date_to": "2026-07-02"},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 2


@pytest.mark.asyncio
async def test_import_duplicate_upload_creates_duplicates(
    client_regular_entries: AsyncClient,
) -> None:
    """Повторная загрузка того же CSV создаёт дубликаты (контракт README)."""
    content = _csv_bytes('"STLT-1","Тема","1","2026-07-05 08:43","u"\n')
    r1 = await client_regular_entries.post(
        f"{TIME_ENTRIES_API}/import-jira-csv",
        files=_files(content),
    )
    assert r1.status_code == 201, r1.text
    r2 = await client_regular_entries.post(
        f"{TIME_ENTRIES_API}/import-jira-csv",
        files=_files(content),
    )
    assert r2.status_code == 201, r2.text
    listed = await client_regular_entries.get(
        TIME_ENTRIES_API,
        params={"date_from": "2026-07-05", "date_to": "2026-07-05"},
    )
    assert listed.json()["total"] == 2


@pytest.mark.asyncio
async def test_import_partial_failure_reports_row_errors(
    client_regular_entries: AsyncClient,
) -> None:
    content = _csv_bytes(
        '"STLT-1","Валидная строка","1","2026-07-01 08:43","u"\n'
        '"STLT-2","","1","2026-07-02 08:43","u"\n'
        '"STLT-3","Битые часы","много","2026-07-03 08:43","u"\n'
    )
    r = await client_regular_entries.post(
        f"{TIME_ENTRIES_API}/import-jira-csv",
        files=_files(content),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["created_count"] == 1
    assert body["skipped_count"] == 2
    assert [e["row"] for e in body["errors"]] == [3, 4]


@pytest.mark.asyncio
async def test_import_rejects_non_csv_extension(
    client_regular_entries: AsyncClient,
) -> None:
    content = _csv_bytes('"STLT-1","Тема","1","2026-07-01 08:43","u"\n')
    r = await client_regular_entries.post(
        f"{TIME_ENTRIES_API}/import-jira-csv",
        files=_files(content, filename="worklog.txt"),
    )
    assert_api_error(r, 422, "validation_error")


@pytest.mark.asyncio
async def test_import_rejects_disallowed_content_type(
    client_regular_entries: AsyncClient,
) -> None:
    content = _csv_bytes('"STLT-1","Тема","1","2026-07-01 08:43","u"\n')
    r = await client_regular_entries.post(
        f"{TIME_ENTRIES_API}/import-jira-csv",
        files=_files(content, content_type="application/pdf"),
    )
    assert_api_error(r, 422, "validation_error")


@pytest.mark.asyncio
async def test_import_rejects_missing_required_columns(
    client_regular_entries: AsyncClient,
) -> None:
    content = '"Ключ задачи","Часов","Дата работы"\n"STLT-1","1","2026-07-01 08:43"\n'.encode()
    r = await client_regular_entries.post(
        f"{TIME_ENTRIES_API}/import-jira-csv",
        files=_files(content),
    )
    assert_api_error(r, 422, "validation_error")


@pytest.mark.asyncio
async def test_import_rejects_oversized_file(client_regular_entries: AsyncClient) -> None:
    content = _csv_bytes('"STLT-1","Тема","1","2026-07-01 08:43","u"\n') + b"x" * 64
    with patch("app.portal_time_entries.routes.time_entries._MAX_CSV_SIZE_BYTES", 32):
        r = await client_regular_entries.post(
            f"{TIME_ENTRIES_API}/import-jira-csv",
            files=_files(content),
        )
    assert_api_error(r, 413, "payload_too_large")


@pytest.mark.asyncio
async def test_import_rejects_non_utf8(client_regular_entries: AsyncClient) -> None:
    r = await client_regular_entries.post(
        f"{TIME_ENTRIES_API}/import-jira-csv",
        files=_files(b"\xff\xfe" + "Тема".encode("utf-16-le")),
    )
    assert_api_error(r, 422, "validation_error")
