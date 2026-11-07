"""HTTP-контракт закупочных заявок: CRUD, summary, роль менеджера."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from tests.portal_finance.conftest import FINANCE_API, assert_api_error

_PROC = f"{FINANCE_API}/procurement-requests"
_CREATE_BODY = {
    "title": "Закупка серверного оборудования",
    "description": "HP ProLiant DL380 x2",
    "amount": "350000.00",
    "currency": "RUB",
    "status": "draft",
}


async def test_procurement_crud_as_admin(client_admin: AsyncClient) -> None:
    r = await client_admin.post(_PROC, json=_CREATE_BODY)
    assert r.status_code == 201, r.text
    created = r.json()
    rid = created["id"]
    assert created["title"] == _CREATE_BODY["title"]
    assert created["status"] == "draft"
    assert created["author_sub"] == "admin-sub"

    r = await client_admin.get(_PROC)
    assert r.status_code == 200
    assert rid in [x["id"] for x in r.json()]

    r = await client_admin.get(f"{_PROC}/{rid}")
    assert r.status_code == 200
    assert r.json()["id"] == rid

    r = await client_admin.patch(f"{_PROC}/{rid}", json={"status": "approved"})
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    r = await client_admin.delete(f"{_PROC}/{rid}")
    assert r.status_code == 204
    r = await client_admin.get(f"{_PROC}/{rid}")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


async def test_procurement_crud_as_manager(client_user: AsyncClient) -> None:
    """client_user — менеджер по gid_number, не отдельная роль «закупщик»."""
    r = await client_user.post(_PROC, json={**_CREATE_BODY, "title": "Закупка ПО"})
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    assert r.json()["author_sub"] == "user-sub"

    r = await client_user.get(_PROC)
    assert r.status_code == 200
    assert rid in [x["id"] for x in r.json()]

    r = await client_user.patch(f"{_PROC}/{rid}", json={"status": "pending_approval"})
    assert r.status_code == 200
    assert r.json()["status"] == "pending_approval"

    r = await client_user.delete(f"{_PROC}/{rid}")
    assert r.status_code == 204


async def test_procurement_unknown_counterparty_returns_404(client_admin: AsyncClient) -> None:
    missing = str(uuid.uuid4())
    r = await client_admin.post(_PROC, json={**_CREATE_BODY, "counterparty_id": missing})
    assert_api_error(r, 404, "not_found")

    r = await client_admin.post(_PROC, json=_CREATE_BODY)
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    r = await client_admin.patch(f"{_PROC}/{rid}", json={"counterparty_id": missing})
    assert_api_error(r, 404, "not_found")


async def test_procurement_summary_empty_and_after_create(client_admin: AsyncClient) -> None:
    r = await client_admin.get(f"{FINANCE_API}/procurement-summary")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 0
    assert data["by_status"] == {}
    assert float(data["total_budget"]) == 0.0

    r = await client_admin.post(_PROC, json=_CREATE_BODY)
    assert r.status_code == 201, r.text
    r = await client_admin.get(f"{FINANCE_API}/procurement-summary")
    data = r.json()
    assert data["total"] == 1
    assert data["by_status"] == {"draft": 1}
    assert float(data["total_budget"]) == 350000.0
