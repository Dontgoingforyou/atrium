"""API персональных настроек канбана специалистов."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

_PREF = "/api/v1/portal/me/specialist-board-pref"


@pytest.mark.asyncio
async def test_specialist_board_pref_get_default_empty(client_manager: AsyncClient) -> None:
    r = await client_manager.get(_PREF)
    assert r.status_code == 200
    body = r.json()
    assert body["column_order"] == []
    assert body["hidden_column_keys"] == []


@pytest.mark.asyncio
async def test_specialist_board_pref_put_get_roundtrip(client_manager: AsyncClient) -> None:
    cols = (await client_manager.get("/api/v1/portal/specialists/columns")).json()
    assert cols
    keys = [c["key"] for c in cols[:2]]
    if len(keys) < 2:
        keys = [cols[0]["key"]]

    body = {"column_order": list(reversed(keys)), "hidden_column_keys": [keys[0]]}
    r = await client_manager.put(_PREF, json=body)
    assert r.status_code == 200
    assert r.json()["column_order"] == body["column_order"]
    assert r.json()["hidden_column_keys"] == body["hidden_column_keys"]

    r2 = await client_manager.get(_PREF)
    assert r2.status_code == 200
    assert r2.json()["column_order"] == body["column_order"]
    assert r2.json()["hidden_column_keys"] == body["hidden_column_keys"]


@pytest.mark.asyncio
async def test_specialist_board_pref_put_drops_unknown_column_keys(client_manager: AsyncClient) -> None:
    """Устаревшие ключи в pref (удалённая колонка) не ломают сохранение скрытия."""
    cols = (await client_manager.get("/api/v1/portal/specialists/columns")).json()
    assert cols
    known_key = cols[0]["key"]
    stale_key = "column_removed_long_ago"
    body = {
        "column_order": [stale_key, known_key],
        "hidden_column_keys": [stale_key, known_key],
    }
    r = await client_manager.put(_PREF, json=body)
    assert r.status_code == 200
    data = r.json()
    assert stale_key not in data["column_order"]
    assert stale_key not in data["hidden_column_keys"]
    assert known_key in data["column_order"]


@pytest.mark.asyncio
async def test_specialist_board_pref_forbidden_for_student(client_specialist_user: AsyncClient) -> None:
    r = await client_specialist_user.get(_PREF)
    assert r.status_code == 403

    r_put = await client_specialist_user.put(_PREF, json={"column_order": [], "hidden_column_keys": []})
    assert r_put.status_code == 403
