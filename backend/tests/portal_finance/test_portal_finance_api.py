"""HTTP-контракт финансов: CRUD, фильтры, summary, валидация."""

from __future__ import annotations

import pytest
from app.infrastructure.db.models.portal_finance import PortalContract, PortalCounterparty, PortalInvoice
from httpx import AsyncClient, Response

from tests.portal_finance.conftest import FINANCE_API

_PAYMENT_BODY = {
    "amount": "10000.00",
    "currency": "RUB",
    "payment_category": "contract",
}


def assert_pydantic_422(response: Response) -> None:
    assert response.status_code == 422, response.text
    assert "detail" in response.json()


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("GET", f"{FINANCE_API}/contracts", {"params": {"limit": 0}}),
        ("GET", f"{FINANCE_API}/contracts", {"params": {"limit": 501}}),
        ("GET", f"{FINANCE_API}/invoices", {"params": {"offset": -1}}),
        ("POST", f"{FINANCE_API}/contracts", {"json": {}}),
        ("POST", f"{FINANCE_API}/invoices", {"json": {"title": "X", "amount": "-1"}}),
        ("DELETE", f"{FINANCE_API}/payments/not-a-uuid", {}),
        ("POST", f"{FINANCE_API}/contracts", {"json": {"title": "X", "status": "nope"}}),
    ],
)
async def test_finance_validation_returns_422(
    client_user: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_user.request(method, path, **kwargs)
    assert_pydantic_422(r)


async def test_counterparty_list_admin_sees_all(
    client_admin: AsyncClient,
    counterparty: PortalCounterparty,
    inactive_counterparty: PortalCounterparty,
) -> None:
    r = await client_admin.get(f"{FINANCE_API}/counterparties")
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()}
    assert str(counterparty.id) in ids
    assert str(inactive_counterparty.id) in ids


async def test_counterparty_list_regular_user_sees_active_only(
    client_user: AsyncClient,
    counterparty: PortalCounterparty,
    inactive_counterparty: PortalCounterparty,
) -> None:
    r = await client_user.get(f"{FINANCE_API}/counterparties")
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()}
    assert str(counterparty.id) in ids
    assert str(inactive_counterparty.id) not in ids


async def test_counterparty_create_and_update_as_admin(
    client_admin: AsyncClient,
    counterparty: PortalCounterparty,
) -> None:
    r = await client_admin.post(
        f"{FINANCE_API}/counterparties",
        json={
            "name": "Новый Поставщик",
            "inn": "5550001234",
            "counterparty_type": "vendor",
            "is_active": True,
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["name"] == "Новый Поставщик"
    assert data["inn"] == "5550001234"
    assert data["is_active"] is True
    assert data["author_sub"] == "admin-sub"

    r = await client_admin.get(f"{FINANCE_API}/counterparties/{counterparty.id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(counterparty.id)

    r = await client_admin.patch(
        f"{FINANCE_API}/counterparties/{counterparty.id}",
        json={"name": "Обновлённое название", "is_active": False},
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Обновлённое название"
    assert r.json()["is_active"] is False


async def test_contract_create_get_update_and_soft_delete(
    client_admin: AsyncClient,
    counterparty: PortalCounterparty,
    contract_row: PortalContract,
) -> None:
    r = await client_admin.post(
        f"{FINANCE_API}/contracts",
        json={
            "title": "Договор аренды серверной",
            "contract_type": "active",
            "counterparty_id": str(counterparty.id),
            "amount": "250000.00",
            "currency": "RUB",
            "status": "draft",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "Договор аренды серверной"
    assert data["status"] == "draft"
    assert data["author_sub"] == "admin-sub"
    assert data["counterparty_id"] == str(counterparty.id)

    r = await client_admin.get(f"{FINANCE_API}/contracts/{contract_row.id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(contract_row.id)

    r = await client_admin.patch(
        f"{FINANCE_API}/contracts/{contract_row.id}",
        json={"title": "Обновлённый договор", "status": "active"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "Обновлённый договор"
    assert r.json()["status"] == "active"

    r = await client_admin.delete(f"{FINANCE_API}/contracts/{contract_row.id}")
    assert r.status_code == 204
    r = await client_admin.get(f"{FINANCE_API}/contracts/{contract_row.id}")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


async def test_contract_list_filters(
    client_admin: AsyncClient,
    counterparty: PortalCounterparty,
    contract_row: PortalContract,
) -> None:
    r = await client_admin.get(f"{FINANCE_API}/contracts", params={"status": "draft"})
    assert r.status_code == 200
    assert str(contract_row.id) in [x["id"] for x in r.json()]

    r = await client_admin.get(f"{FINANCE_API}/contracts", params={"status": "active"})
    assert r.status_code == 200
    assert str(contract_row.id) not in [x["id"] for x in r.json()]

    r = await client_admin.get(f"{FINANCE_API}/contracts", params={"contract_type": "active"})
    assert r.status_code == 200
    assert str(contract_row.id) in [x["id"] for x in r.json()]

    r = await client_admin.get(
        f"{FINANCE_API}/contracts",
        params={"counterparty_id": str(counterparty.id)},
    )
    assert r.status_code == 200
    assert str(contract_row.id) in [x["id"] for x in r.json()]
    assert all(x["counterparty_id"] == str(counterparty.id) for x in r.json())


async def test_invoice_create_get_update_and_filters(
    client_admin: AsyncClient,
    contract_row: PortalContract,
    invoice_row: PortalInvoice,
) -> None:
    r = await client_admin.post(
        f"{FINANCE_API}/invoices",
        json={
            "title": "Счёт на поставку ПО",
            "contract_id": str(contract_row.id),
            "invoice_type": "invoice",
            "amount": "75000.00",
            "currency": "RUB",
            "status": "draft",
        },
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["title"] == "Счёт на поставку ПО"
    assert data["status"] == "draft"
    assert data["author_sub"] == "admin-sub"
    assert data["contract_id"] == str(contract_row.id)

    r = await client_admin.get(f"{FINANCE_API}/invoices/{invoice_row.id}")
    assert r.status_code == 200
    assert r.json()["id"] == str(invoice_row.id)

    r = await client_admin.patch(f"{FINANCE_API}/invoices/{invoice_row.id}", json={"status": "sent"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "sent"

    r = await client_admin.get(f"{FINANCE_API}/invoices", params={"status": "sent"})
    assert r.status_code == 200
    assert str(invoice_row.id) in [x["id"] for x in r.json()]

    r = await client_admin.get(f"{FINANCE_API}/invoices", params={"status": "paid"})
    assert r.status_code == 200
    assert str(invoice_row.id) not in [x["id"] for x in r.json()]

    r = await client_admin.get(f"{FINANCE_API}/invoices", params={"invoice_type": "invoice"})
    assert r.status_code == 200
    assert str(invoice_row.id) in [x["id"] for x in r.json()]

    r = await client_admin.get(
        f"{FINANCE_API}/invoices",
        params={"contract_id": str(contract_row.id)},
    )
    assert r.status_code == 200
    assert str(invoice_row.id) in [x["id"] for x in r.json()]
    assert all(x["contract_id"] == str(contract_row.id) for x in r.json())


async def test_payment_create_list_filter_and_delete(
    client_admin: AsyncClient,
    invoice_row: PortalInvoice,
) -> None:
    r = await client_admin.post(
        f"{FINANCE_API}/payments",
        json={**_PAYMENT_BODY, "invoice_id": str(invoice_row.id)},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["amount"] == "10000.00"
    assert data["currency"] == "RUB"
    assert data["author_sub"] == "admin-sub"
    assert data["invoice_id"] == str(invoice_row.id)
    pid = data["id"]

    r = await client_admin.post(f"{FINANCE_API}/payments", json=_PAYMENT_BODY)
    assert r.status_code == 201, r.text
    assert r.json()["invoice_id"] is None

    r = await client_admin.get(f"{FINANCE_API}/payments")
    assert r.status_code == 200
    assert pid in [x["id"] for x in r.json()]

    r = await client_admin.get(
        f"{FINANCE_API}/payments",
        params={"invoice_id": str(invoice_row.id)},
    )
    assert r.status_code == 200
    assert pid in [x["id"] for x in r.json()]
    assert all(x["invoice_id"] == str(invoice_row.id) for x in r.json())

    r = await client_admin.delete(f"{FINANCE_API}/payments/{pid}")
    assert r.status_code == 204


async def test_summary_empty_db(client_admin: AsyncClient) -> None:
    r = await client_admin.get(f"{FINANCE_API}/summary")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["contracts_total"] == 0
    assert data["contracts_active"] == 0
    assert data["invoices_total"] == 0
    assert data["payments_count"] == 0
    assert data["payments_total_amount"] == "0.00" or float(data["payments_total_amount"]) == 0.0


async def test_summary_counts_exact(
    client_admin: AsyncClient,
    contract_row: PortalContract,
    invoice_row: PortalInvoice,
) -> None:
    r = await client_admin.get(f"{FINANCE_API}/summary")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["contracts_total"] == 1
    assert data["invoices_total"] == 1
    assert data["contracts_active"] == 0

    r = await client_admin.patch(
        f"{FINANCE_API}/contracts/{contract_row.id}",
        json={"status": "active"},
    )
    assert r.status_code == 200
    r = await client_admin.get(f"{FINANCE_API}/summary")
    assert r.json()["contracts_active"] == 1

    r = await client_admin.post(
        f"{FINANCE_API}/payments",
        json={**_PAYMENT_BODY, "invoice_id": str(invoice_row.id)},
    )
    assert r.status_code == 201
    r = await client_admin.get(f"{FINANCE_API}/summary")
    data = r.json()
    assert data["payments_count"] == 1
    assert float(data["payments_total_amount"]) == 10000.0
