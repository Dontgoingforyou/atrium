"""RBAC / 401 / 403: матрица REST portal_time_entries."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.portal_time_entries.conftest import TIME_ENTRIES_API, assert_api_error

_AUTH_UUID = "00000000-0000-4000-8000-000000000001"
_MONTH = "2026-04"

_CREATE_BODY = {"worked_on": "2026-04-01", "minutes": 60, "note": "тест"}
_BULK_BODY = {"date_from": "2026-06-01", "date_to": "2026-06-05", "minutes": 30}
_CSV_HEADER = '"Ключ задачи","Тема задачи","Часов","Дата работы","Имя пользователя"\n'
_CSV_ROW = '"STLT-1","Тема","1","2026-07-01 08:43","u"\n'


def _import_files() -> dict[str, tuple[str, bytes, str]]:
    content = (_CSV_HEADER + _CSV_ROW).encode("utf-8")
    return {"file": ("worklog.csv", content, "text/csv")}


def _get_routes() -> list[tuple[str, str, dict[str, object]]]:
    return [
        ("GET", TIME_ENTRIES_API, {}),
        ("GET", f"{TIME_ENTRIES_API}/summary", {"params": {"date_from": "2026-04-01", "date_to": "2026-04-30"}}),
        ("GET", f"{TIME_ENTRIES_API}/report", {"params": {"group_by": "month"}}),
        ("GET", f"{TIME_ENTRIES_API}/specialists", {"params": {"month": _MONTH}}),
        (
            "GET",
            f"{TIME_ENTRIES_API}/export",
            {"params": {"format": "csv", "month": _MONTH}},
        ),
        ("POST", TIME_ENTRIES_API, {"json": _CREATE_BODY}),
        ("POST", f"{TIME_ENTRIES_API}/bulk", {"json": _BULK_BODY}),
        ("POST", f"{TIME_ENTRIES_API}/import-jira-csv", {"files": _import_files()}),
        ("PATCH", f"{TIME_ENTRIES_API}/{_AUTH_UUID}", {"json": {"expected_version": 1, "minutes": 99}}),
        ("DELETE", f"{TIME_ENTRIES_API}/{_AUTH_UUID}", {}),
    ]


@pytest.mark.parametrize(("method", "path", "kwargs"), _get_routes())
async def test_time_entries_require_auth(
    client_sqlite_only: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_sqlite_only.request(method, path, **kwargs)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize(("method", "path", "kwargs"), _get_routes())
async def test_time_entries_forbidden_without_timesheets_access(
    client_no_idp: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_no_idp.request(method, path, **kwargs)
    assert_api_error(r, 403, "forbidden")


@pytest.mark.parametrize(("method", "path", "kwargs"), _get_routes())
async def test_time_entries_outstaff_without_gid_forbidden(
    client_outstaff_not_manager: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_outstaff_not_manager.request(method, path, **kwargs)
    assert_api_error(r, 403, "forbidden")


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", f"{TIME_ENTRIES_API}/specialists", {"params": {"month": _MONTH}}),
    ],
)
async def test_specialists_forbidden_for_developer(
    client_developer: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_developer.request(method, path, **kwargs)
    assert_api_error(r, 403, "forbidden")


@pytest.mark.parametrize(
    ("path", "params"),
    [
        (TIME_ENTRIES_API, {"user_sub": "other-sub"}),
        (f"{TIME_ENTRIES_API}/summary", {"user_sub": "other-sub"}),
        (f"{TIME_ENTRIES_API}/report", {"user_sub": "other-sub"}),
        (
            f"{TIME_ENTRIES_API}/export",
            {"format": "csv", "month": _MONTH, "user_sub": "other-sub"},
        ),
    ],
)
async def test_developer_cannot_filter_other_user_sub(
    client_developer: AsyncClient,
    path: str,
    params: dict[str, str],
) -> None:
    r = await client_developer.get(path, params=params)
    assert_api_error(r, 403, "forbidden")


@pytest.mark.parametrize(
    ("path", "params"),
    [
        (TIME_ENTRIES_API, {"user_sub": "user-b"}),
        (f"{TIME_ENTRIES_API}/summary", {"user_sub": "user-b"}),
        (f"{TIME_ENTRIES_API}/report", {"user_sub": "user-b"}),
        (
            f"{TIME_ENTRIES_API}/export",
            {"format": "csv", "month": _MONTH, "user_sub": "user-b"},
        ),
    ],
)
async def test_no_idp_cannot_filter_other_user_sub(
    client_no_idp: AsyncClient,
    path: str,
    params: dict[str, str],
) -> None:
    r = await client_no_idp.get(path, params=params)
    assert_api_error(r, 403, "forbidden")
