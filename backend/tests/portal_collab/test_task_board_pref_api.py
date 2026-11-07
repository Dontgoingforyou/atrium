"""API персональных настроек канбана задач."""

from __future__ import annotations

import pytest
from app.portal_collab.schemas.task import TaskBoardPrefWrite
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_regular, user_portal_user_b
from tests.portal_collab.conftest import async_client_as

_PREF = "/api/v1/portal/me/task-board-pref"


@pytest.mark.asyncio
async def test_task_board_pref_get_default_empty(client_user: AsyncClient) -> None:
    r = await client_user.get(_PREF)
    assert r.status_code == 200
    data = r.json()
    assert data["column_order"] == []
    assert data["hidden_status_keys"] == []
    assert data["title_overrides"] == {}
    assert data["subtasks_flat"] is False
    assert data["hide_subtasks"] is False


@pytest.mark.asyncio
async def test_task_board_pref_put_get_roundtrip(client_user: AsyncClient) -> None:
    body = {
        "column_order": ["done", "todo", "in_progress"],
        "hidden_status_keys": ["cancelled"],
        "title_overrides": {"todo": "Входящие"},
        "subtasks_flat": True,
        "hide_subtasks": False,
    }
    r = await client_user.put(_PREF, json=body)
    assert r.status_code == 200
    assert r.json()["column_order"] == ["done", "todo", "in_progress"]
    assert r.json()["subtasks_flat"] is True

    r2 = await client_user.get(_PREF)
    assert r2.status_code == 200
    got = r2.json()
    assert got["column_order"] == ["done", "todo", "in_progress"]
    assert got["hidden_status_keys"] == ["cancelled"]
    assert got["title_overrides"] == {"todo": "Входящие"}
    assert got["subtasks_flat"] is True
    assert got["hide_subtasks"] is False


@pytest.mark.asyncio
async def test_task_board_pref_hide_subtasks_clears_flat(client_user: AsyncClient) -> None:
    r = await client_user.put(
        _PREF,
        json={
            "column_order": [],
            "hidden_status_keys": [],
            "title_overrides": {},
            "subtasks_flat": True,
            "hide_subtasks": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["hide_subtasks"] is True
    assert data["subtasks_flat"] is False


@pytest.mark.asyncio
async def test_task_board_pref_isolated_per_user(
    sqlite_session: AsyncSession,
    patch_oidc_settings: object,
) -> None:
    async with async_client_as(sqlite_session, user_portal_regular) as ac_a:
        r_put = await ac_a.put(
            _PREF,
            json={
                "column_order": ["done"],
                "hidden_status_keys": ["cancelled"],
                "title_overrides": {},
            },
        )
        assert r_put.status_code == 200

    async with async_client_as(sqlite_session, user_portal_user_b) as ac_b:
        r_b = await ac_b.get(_PREF)
        assert r_b.status_code == 200
        assert r_b.json()["column_order"] == []
        assert r_b.json()["hidden_status_keys"] == []


@pytest.mark.asyncio
async def test_task_board_pref_validation_max_order(client_user: AsyncClient) -> None:
    r = await client_user.put(
        _PREF,
        json={
            "column_order": ["s"] * 65,
            "hidden_status_keys": [],
            "title_overrides": {},
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_task_board_pref_merge_order_logic() -> None:
    from app.portal_collab.schemas.task import TaskBoardPrefRead

    pref = TaskBoardPrefRead(
        column_order=["done", "todo"],
        hidden_status_keys=[],
        title_overrides={},
    )
    column_keys = ["todo", "in_progress", "done", "cancelled"]
    order = [k for k in pref.column_order if k in column_keys]
    for k in column_keys:
        if k not in order:
            order.append(k)
    assert order == ["done", "todo", "in_progress", "cancelled"]


@pytest.mark.parametrize(
    ("field", "payload", "match_substr"),
    [
        (
            "column_order",
            {"column_order": ["x" * 33], "hidden_status_keys": [], "title_overrides": {}},
            "32",
        ),
        (
            "hidden_status_keys",
            {"column_order": [], "hidden_status_keys": ["y" * 33], "title_overrides": {}},
            "32",
        ),
        (
            "title_overrides_count",
            {
                "column_order": [],
                "hidden_status_keys": [],
                "title_overrides": {f"k{i}": "v" for i in range(33)},
            },
            "32",
        ),
        (
            "title_overrides_key_len",
            {
                "column_order": [],
                "hidden_status_keys": [],
                "title_overrides": {"z" * 33: "ok"},
            },
            "32",
        ),
        (
            "title_overrides_value_len",
            {
                "column_order": [],
                "hidden_status_keys": [],
                "title_overrides": {"todo": "t" * 129},
            },
            "128",
        ),
    ],
)
def test_task_board_pref_write_validators(field: str, payload: dict, match_substr: str) -> None:
    with pytest.raises(ValidationError, match=match_substr):
        TaskBoardPrefWrite.model_validate(payload)
