"""RBAC / 401 / timesheet 403: матрица REST portal_specialists."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.portal_specialists.conftest import (
    _AUTH_UUID,
    SPECIALISTS_API,
    assert_api_error,
)

_PREF = "/api/v1/portal/me/specialist-board-pref"
_SPEC = "specialist-sub"


def _reorder_body() -> dict[str, object]:
    return {
        "entry_id": _AUTH_UUID,
        "column_key": "new",
        "after_entry_id": None,
        "before_entry_id": None,
    }


def _pref_body() -> dict[str, object]:
    return {"column_order": [], "hidden_column_keys": []}


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", f"{SPECIALISTS_API}/columns", {}),
        ("POST", f"{SPECIALISTS_API}/columns", {"json": {"key": "x", "title": "X", "color": "#000"}}),
        ("PATCH", f"{SPECIALISTS_API}/columns/{_AUTH_UUID}", {"json": {"title": "Y"}}),
        ("DELETE", f"{SPECIALISTS_API}/columns/{_AUTH_UUID}", {}),
        ("GET", f"{SPECIALISTS_API}/statuses", {}),
        ("POST", f"{SPECIALISTS_API}/statuses", {"json": {"title": "S", "color": "#111"}}),
        ("PATCH", f"{SPECIALISTS_API}/statuses/{_AUTH_UUID}", {"json": {"title": "S2"}}),
        ("DELETE", f"{SPECIALISTS_API}/statuses/{_AUTH_UUID}", {}),
        ("GET", f"{SPECIALISTS_API}/board", {}),
        ("GET", f"{SPECIALISTS_API}/board", {"params": {"directory": "true"}}),
        (
            "POST",
            f"{SPECIALISTS_API}/board",
            {"json": {"specialist_sub": _SPEC, "column_key": "new"}},
        ),
        ("PATCH", f"{SPECIALISTS_API}/board/{_SPEC}", {"json": {"expected_version": 1, "column_key": "cv_sent"}}),
        ("POST", f"{SPECIALISTS_API}/board/reorder", {"json": _reorder_body()}),
        (
            "POST",
            f"{SPECIALISTS_API}/board/{_SPEC}/reassign-manager",
            {"json": {"from_manager_sub": "a", "to_manager_sub": "b"}},
        ),
        ("DELETE", f"{SPECIALISTS_API}/board/{_SPEC}", {}),
        ("GET", f"{SPECIALISTS_API}/board/by-specialist", {"params": {"specialist_sub": _SPEC}}),
        ("GET", f"{SPECIALISTS_API}/{_SPEC}/profile", {}),
        ("PATCH", f"{SPECIALISTS_API}/{_SPEC}/profile", {"json": {"expected_version": 1, "location": "X"}}),
        ("DELETE", f"{SPECIALISTS_API}/{_SPEC}", {}),
        ("GET", f"{SPECIALISTS_API}/{_SPEC}/links", {}),
        (
            "POST",
            f"{SPECIALISTS_API}/{_SPEC}/links",
            {"json": {"title": "L", "url": "https://example.com"}},
        ),
        ("DELETE", f"{SPECIALISTS_API}/{_SPEC}/links/{_AUTH_UUID}", {}),
        ("GET", f"{SPECIALISTS_API}/{_SPEC}/notes", {}),
        ("POST", f"{SPECIALISTS_API}/{_SPEC}/notes", {"json": {"body": "n"}}),
        ("PATCH", f"{SPECIALISTS_API}/{_SPEC}/notes/{_AUTH_UUID}", {"json": {"body": "x"}}),
        ("DELETE", f"{SPECIALISTS_API}/{_SPEC}/notes/{_AUTH_UUID}", {}),
        ("GET", _PREF, {}),
        ("PUT", _PREF, {"json": _pref_body()}),
        ("GET", f"{SPECIALISTS_API}/jira/search", {"params": {"q": "ab"}}),
        ("GET", f"{SPECIALISTS_API}/{_SPEC}/jira", {}),
        (
            "POST",
            f"{SPECIALISTS_API}/{_SPEC}/jira/link",
            {"json": {"issue_key": "BASE-1"}},
        ),
        ("POST", f"{SPECIALISTS_API}/{_SPEC}/jira/sync", {}),
        ("DELETE", f"{SPECIALISTS_API}/{_SPEC}/jira/link", {}),
        ("POST", f"{SPECIALISTS_API}/columns/sync-from-jira", {}),
        ("POST", f"{SPECIALISTS_API}/board/ws-ticket", {}),
    ],
)
async def test_specialists_endpoints_require_auth(
    client_sqlite_only_board: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_sqlite_only_board.request(method, path, **kwargs)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", f"{SPECIALISTS_API}/columns", {}),
        ("POST", f"{SPECIALISTS_API}/columns", {"json": {"key": "x", "title": "X", "color": "#000"}}),
        ("GET", f"{SPECIALISTS_API}/statuses", {}),
        ("POST", f"{SPECIALISTS_API}/statuses", {"json": {"title": "S", "color": "#111"}}),
        ("GET", f"{SPECIALISTS_API}/board", {}),
        (
            "POST",
            f"{SPECIALISTS_API}/board",
            {"json": {"specialist_sub": _SPEC, "column_key": "new"}},
        ),
        ("POST", f"{SPECIALISTS_API}/board/reorder", {"json": _reorder_body()}),
        ("GET", f"{SPECIALISTS_API}/{_SPEC}/profile", {}),
        ("PATCH", f"{SPECIALISTS_API}/{_SPEC}/profile", {"json": {"expected_version": 1, "location": "X"}}),
        (
            "POST",
            f"{SPECIALISTS_API}/{_SPEC}/links",
            {"json": {"title": "L", "url": "https://example.com"}},
        ),
        ("POST", f"{SPECIALISTS_API}/{_SPEC}/notes", {"json": {"body": "n"}}),
        ("GET", _PREF, {}),
        ("PUT", _PREF, {"json": _pref_body()}),
        ("GET", f"{SPECIALISTS_API}/jira/search", {"params": {"q": "ab"}}),
        ("POST", f"{SPECIALISTS_API}/board/ws-ticket", {}),
    ],
)
async def test_timesheet_only_forbidden_on_specialists_routes(
    client_developer_board: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_developer_board.request(method, path, **kwargs)
    assert_api_error(r, 403, "forbidden")
