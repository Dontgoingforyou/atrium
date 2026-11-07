"""RBAC / IDOR / 401 финансов: матрица auth, timesheet, write-403, unknown 404."""

from __future__ import annotations

import uuid

import pytest
from app.infrastructure.db.models.portal_finance import (
    PortalContract,
    PortalCounterparty,
    PortalInvoice,
    PortalPayment,
)
from httpx import AsyncClient

from tests.helpers.portal_test_users import user_outstaff_not_manager, user_portal_no_idp_groups
from tests.portal_finance.conftest import (
    FINANCE_API,
    as_user,
    as_user_b,
    as_user_regular,
    assert_api_error,
)

_AUTH_UUID = "00000000-0000-4000-8000-000000000001"
_PROC = f"{FINANCE_API}/procurement-requests"

_AUTH_CASES: list[tuple[str, str, dict[str, object]]] = [
    ("GET", f"{FINANCE_API}/counterparties", {}),
    ("POST", f"{FINANCE_API}/counterparties", {"json": {"name": "X"}}),
    ("GET", f"{FINANCE_API}/counterparties/{_AUTH_UUID}", {}),
    ("PATCH", f"{FINANCE_API}/counterparties/{_AUTH_UUID}", {"json": {"name": "X"}}),
    ("GET", f"{FINANCE_API}/contracts", {}),
    ("POST", f"{FINANCE_API}/contracts", {"json": {"title": "X"}}),
    ("GET", f"{FINANCE_API}/contracts/{_AUTH_UUID}", {}),
    ("PATCH", f"{FINANCE_API}/contracts/{_AUTH_UUID}", {"json": {"title": "X"}}),
    ("DELETE", f"{FINANCE_API}/contracts/{_AUTH_UUID}", {}),
    ("GET", f"{FINANCE_API}/invoices", {}),
    ("POST", f"{FINANCE_API}/invoices", {"json": {"title": "X"}}),
    ("GET", f"{FINANCE_API}/invoices/{_AUTH_UUID}", {}),
    ("PATCH", f"{FINANCE_API}/invoices/{_AUTH_UUID}", {"json": {"title": "X"}}),
    ("GET", f"{FINANCE_API}/payments", {}),
    ("POST", f"{FINANCE_API}/payments", {"json": {"amount": "1.00", "payment_category": "contract"}}),
    ("DELETE", f"{FINANCE_API}/payments/{_AUTH_UUID}", {}),
    ("GET", f"{FINANCE_API}/summary", {}),
    ("GET", _PROC, {}),
    ("POST", _PROC, {"json": {"title": "X"}}),
    ("GET", f"{_PROC}/{_AUTH_UUID}", {}),
    ("PATCH", f"{_PROC}/{_AUTH_UUID}", {"json": {"title": "X"}}),
    ("DELETE", f"{_PROC}/{_AUTH_UUID}", {}),
    ("GET", f"{FINANCE_API}/procurement-summary", {}),
]


@pytest.mark.parametrize(("method", "path", "kwargs"), _AUTH_CASES)
async def test_finance_endpoints_require_auth(
    client_sqlite_only: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_sqlite_only.request(method, path, **kwargs)
    assert_api_error(r, 401, "unauthorized")


@pytest.mark.parametrize(("method", "path", "kwargs"), _AUTH_CASES)
async def test_timesheet_forbidden_on_finance(
    client_developer: AsyncClient,
    method: str,
    path: str,
    kwargs: dict[str, object],
) -> None:
    r = await client_developer.request(method, path, **kwargs)
    assert_api_error(r, 403, "forbidden")


async def test_counterparty_write_requires_admin(
    client_user: AsyncClient,
    counterparty: PortalCounterparty,
) -> None:
    r = await client_user.post(
        f"{FINANCE_API}/counterparties",
        json={"name": "Попытка создания", "counterparty_type": "vendor"},
    )
    assert_api_error(r, 403, "forbidden")
    r = await client_user.patch(
        f"{FINANCE_API}/counterparties/{counterparty.id}",
        json={"name": "Взлом"},
    )
    assert_api_error(r, 403, "forbidden")


async def test_inactive_counterparty_hidden_from_regular(
    client_user: AsyncClient,
    inactive_counterparty: PortalCounterparty,
) -> None:
    r = await client_user.get(f"{FINANCE_API}/counterparties/{inactive_counterparty.id}")
    assert_api_error(r, 404, "not_found")


async def test_regular_cannot_bind_inactive_counterparty_to_contract(
    client_user: AsyncClient,
    inactive_counterparty: PortalCounterparty,
) -> None:
    r = await client_user.post(
        f"{FINANCE_API}/contracts",
        json={
            "title": "Договор с неактивным",
            "contract_type": "active",
            "counterparty_id": str(inactive_counterparty.id),
            "status": "draft",
        },
    )
    assert_api_error(r, 404, "not_found")


async def test_unknown_ids_return_404(
    client_admin: AsyncClient,
    contract_row: PortalContract,
    invoice_row: PortalInvoice,
) -> None:
    missing = uuid.uuid4()
    r = await client_admin.get(f"{FINANCE_API}/counterparties/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.patch(f"{FINANCE_API}/counterparties/{missing}", json={"name": "X"})
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{FINANCE_API}/contracts/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.patch(f"{FINANCE_API}/contracts/{missing}", json={"title": "X"})
    assert_api_error(r, 404, "not_found")
    r = await client_admin.delete(f"{FINANCE_API}/contracts/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{FINANCE_API}/invoices/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.patch(f"{FINANCE_API}/invoices/{missing}", json={"title": "X"})
    assert_api_error(r, 404, "not_found")
    r = await client_admin.delete(f"{FINANCE_API}/payments/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.get(f"{_PROC}/{missing}")
    assert_api_error(r, 404, "not_found")
    r = await client_admin.patch(f"{_PROC}/{missing}", json={"title": "X"})
    assert_api_error(r, 404, "not_found")
    r = await client_admin.delete(f"{_PROC}/{missing}")
    assert_api_error(r, 404, "not_found")

    r = await client_admin.post(
        f"{FINANCE_API}/contracts",
        json={"title": "Без контрагента", "counterparty_id": str(missing)},
    )
    assert_api_error(r, 404, "not_found")
    r = await client_admin.patch(
        f"{FINANCE_API}/contracts/{contract_row.id}",
        json={"counterparty_id": str(missing)},
    )
    assert_api_error(r, 404, "not_found")
    r = await client_admin.post(
        f"{FINANCE_API}/invoices",
        json={"title": "Счёт", "contract_id": str(missing)},
    )
    assert_api_error(r, 404, "not_found")
    r = await client_admin.patch(
        f"{FINANCE_API}/invoices/{invoice_row.id}",
        json={"contract_id": str(missing)},
    )
    assert_api_error(r, 404, "not_found")
    r = await client_admin.post(
        f"{FINANCE_API}/payments",
        json={"amount": "1.00", "payment_category": "contract", "invoice_id": str(missing)},
    )
    assert_api_error(r, 404, "not_found")


async def test_foreign_contract_invoice_payment_write_forbidden(
    client_admin: AsyncClient,
    contract_row: PortalContract,
    contract_row_user_b: PortalContract,
    invoice_row: PortalInvoice,
    invoice_row_user_b: PortalInvoice,
    payment_row: PortalPayment,
) -> None:
    with as_user_regular():
        r = await client_admin.patch(
            f"{FINANCE_API}/contracts/{contract_row.id}",
            json={"title": "Хакерское изменение"},
        )
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.delete(f"{FINANCE_API}/contracts/{contract_row.id}")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.patch(
            f"{FINANCE_API}/invoices/{invoice_row.id}",
            json={"title": "Несанкционированное изменение"},
        )
        assert_api_error(r, 403, "forbidden")
    with as_user_b():
        r = await client_admin.delete(f"{FINANCE_API}/payments/{payment_row.id}")
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.patch(
            f"{FINANCE_API}/contracts/{contract_row_user_b.id}",
            json={"title": "Свой договор — правка"},
        )
        assert r.status_code == 200, r.text
        r = await client_admin.delete(f"{FINANCE_API}/contracts/{contract_row_user_b.id}")
        assert r.status_code == 204
        r = await client_admin.get(f"{FINANCE_API}/contracts/{contract_row_user_b.id}")
        assert r.status_code == 200
        assert r.json()["status"] == "cancelled"
        r = await client_admin.patch(
            f"{FINANCE_API}/invoices/{invoice_row_user_b.id}",
            json={"status": "sent"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "sent"


async def test_finance_objects_globally_readable(
    client_admin: AsyncClient,
    contract_row: PortalContract,
    invoice_row: PortalInvoice,
    payment_row: PortalPayment,
) -> None:
    created = await client_admin.post(_PROC, json={"title": "Видимая заявка"})
    assert created.status_code == 201, created.text
    rid = created.json()["id"]
    with as_user_regular():
        r = await client_admin.get(f"{FINANCE_API}/contracts/{contract_row.id}")
        assert r.status_code == 200
        assert r.json()["id"] == str(contract_row.id)
        r = await client_admin.get(f"{FINANCE_API}/invoices/{invoice_row.id}")
        assert r.status_code == 200
        assert r.json()["id"] == str(invoice_row.id)
        r = await client_admin.get(f"{FINANCE_API}/payments")
        assert r.status_code == 200
        assert str(payment_row.id) in {item["id"] for item in r.json()}
        r = await client_admin.get(f"{_PROC}/{rid}")
        assert r.status_code == 200
        assert r.json()["id"] == rid


async def test_regular_creates_invoice_on_any_contract(
    client_user: AsyncClient,
    contract_row: PortalContract,
) -> None:
    r = await client_user.post(
        f"{FINANCE_API}/invoices",
        json={
            "title": "Счёт на договор",
            "contract_id": str(contract_row.id),
            "invoice_type": "invoice",
            "amount": "10.00",
            "currency": "RUB",
            "status": "draft",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["contract_id"] == str(contract_row.id)
    assert r.json()["author_sub"] == "user-sub"


async def test_payment_author_deletes_own(client_user: AsyncClient) -> None:
    r = await client_user.post(
        f"{FINANCE_API}/payments",
        json={"amount": "10.00", "currency": "RUB", "payment_category": "contract"},
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    r = await client_user.delete(f"{FINANCE_API}/payments/{pid}")
    assert r.status_code == 204


async def test_owner_sub_only_admin_can_set(
    client_admin: AsyncClient,
    counterparty: PortalCounterparty,
    contract_row_user_b: PortalContract,
) -> None:
    with as_user_regular():
        r = await client_admin.post(
            f"{FINANCE_API}/contracts",
            json={
                "title": "Договор",
                "contract_type": "active",
                "counterparty_id": str(counterparty.id),
                "status": "draft",
                "owner_sub": "intruder-sub",
            },
        )
        assert r.status_code == 201, r.text
        assert r.json()["owner_sub"] == "user-sub"
    with as_user_b():
        r = await client_admin.patch(
            f"{FINANCE_API}/contracts/{contract_row_user_b.id}",
            json={"owner_sub": "intruder-sub"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["owner_sub"] == "user-b"

    r = await client_admin.post(
        f"{FINANCE_API}/contracts",
        json={
            "title": "Админ задаёт владельца",
            "contract_type": "active",
            "counterparty_id": str(counterparty.id),
            "status": "draft",
            "owner_sub": "user-b",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["owner_sub"] == "user-b"


async def test_procurement_create_forbidden_without_manager(
    client_admin: AsyncClient,
) -> None:
    body = {"title": "Закупка без роли"}
    with as_user(user_portal_no_idp_groups):
        r = await client_admin.post(_PROC, json=body)
        assert_api_error(r, 403, "forbidden")
    with as_user(user_outstaff_not_manager):
        r = await client_admin.post(_PROC, json=body)
        assert_api_error(r, 403, "forbidden")


async def test_procurement_foreign_write_forbidden(client_admin: AsyncClient) -> None:
    r = await client_admin.post(_PROC, json={"title": "Чужая заявка"})
    assert r.status_code == 201, r.text
    rid = r.json()["id"]
    with as_user_b():
        r = await client_admin.patch(f"{_PROC}/{rid}", json={"title": "Хакерское"})
        assert_api_error(r, 403, "forbidden")
        r = await client_admin.delete(f"{_PROC}/{rid}")
        assert_api_error(r, 403, "forbidden")
