from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from decimal import Decimal

import pytest
from app.api.deps_auth import get_current_user
from app.infrastructure.db.models.portal_finance import PortalContract, PortalCounterparty, PortalInvoice, PortalPayment
from app.main import app
from app.schemas.auth import UserPublic
from httpx import Response
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_regular, user_portal_user_b

FINANCE_API = "/api/v1/portal/finance"


def assert_api_error(response: Response, status: int, code: str) -> None:
    """Ошибка AppError: и HTTP-статус, и контрактный `code`."""
    assert response.status_code == status, response.text
    assert response.json()["code"] == code


@contextmanager
def override_dependency(
    dependency: object,
    override: object,
) -> Iterator[None]:
    """Подменить Depends без clear()."""
    previous = app.dependency_overrides.get(dependency)
    app.dependency_overrides[dependency] = override
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[dependency] = previous
        else:
            app.dependency_overrides.pop(dependency, None)


@contextmanager
def as_user(user_factory: Callable[[], UserPublic]) -> Iterator[None]:
    """Временно подменить get_current_user без clear()."""
    previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = user_factory
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[get_current_user] = previous
        else:
            app.dependency_overrides.pop(get_current_user, None)


@contextmanager
def as_user_regular() -> Iterator[None]:
    with as_user(user_portal_regular):
        yield


@contextmanager
def as_user_b() -> Iterator[None]:
    with as_user(user_portal_user_b):
        yield


@pytest.fixture
async def counterparty(sqlite_session: AsyncSession) -> PortalCounterparty:
    """Активный контрагент, созданный администратором."""
    row = PortalCounterparty(
        name="ООО Тест-Поставщик",
        inn="1234567890",
        counterparty_type="vendor",
        is_active=True,
        author_sub="admin-sub",
    )
    sqlite_session.add(row)
    await sqlite_session.commit()
    await sqlite_session.refresh(row)
    return row


@pytest.fixture
async def inactive_counterparty(sqlite_session: AsyncSession) -> PortalCounterparty:
    """Неактивный контрагент (не виден обычным пользователям)."""
    row = PortalCounterparty(
        name="ООО Неактивный",
        inn="9999999999",
        counterparty_type="vendor",
        is_active=False,
        author_sub="admin-sub",
    )
    sqlite_session.add(row)
    await sqlite_session.commit()
    await sqlite_session.refresh(row)
    return row


@pytest.fixture
async def contract_row(
    sqlite_session: AsyncSession,
    counterparty: PortalCounterparty,
) -> PortalContract:
    """Договор, созданный администратором (author_sub='admin-sub')."""
    row = PortalContract(
        title="Договор поставки оборудования",
        contract_type="active",
        counterparty_id=counterparty.id,
        amount=Decimal("100000.00"),
        currency="RUB",
        status="draft",
        author_sub="admin-sub",
    )
    sqlite_session.add(row)
    await sqlite_session.commit()
    await sqlite_session.refresh(row)
    return row


@pytest.fixture
async def contract_row_user_b(sqlite_session: AsyncSession) -> PortalContract:
    """Договор, созданный пользователем B (author_sub='user-b')."""
    row = PortalContract(
        title="Договор пользователя B",
        contract_type="active",
        amount=Decimal("10000.00"),
        currency="RUB",
        status="draft",
        author_sub="user-b",
        owner_sub="user-b",
    )
    sqlite_session.add(row)
    await sqlite_session.commit()
    await sqlite_session.refresh(row)
    return row


@pytest.fixture
async def invoice_row(
    sqlite_session: AsyncSession,
    contract_row: PortalContract,
) -> PortalInvoice:
    """Счёт на оплату, созданный администратором (author_sub='admin-sub')."""
    row = PortalInvoice(
        title="Счёт №1 по договору",
        contract_id=contract_row.id,
        invoice_type="invoice",
        amount=Decimal("50000.00"),
        currency="RUB",
        status="draft",
        author_sub="admin-sub",
    )
    sqlite_session.add(row)
    await sqlite_session.commit()
    await sqlite_session.refresh(row)
    return row


@pytest.fixture
async def invoice_row_user_b(sqlite_session: AsyncSession) -> PortalInvoice:
    """Счёт, созданный пользователем B (author_sub='user-b')."""
    row = PortalInvoice(
        title="Счёт пользователя B",
        invoice_type="invoice",
        amount=Decimal("5000.00"),
        currency="RUB",
        status="draft",
        author_sub="user-b",
    )
    sqlite_session.add(row)
    await sqlite_session.commit()
    await sqlite_session.refresh(row)
    return row


@pytest.fixture
async def payment_row(sqlite_session: AsyncSession) -> PortalPayment:
    """Платёж, созданный администратором (author_sub='admin-sub').

    Используется в тестах 403 — запрещает удаление другим пользователем
    без риска конкуренции между dependency_overrides двух клиентов.
    """
    row = PortalPayment(
        amount=Decimal("15000.00"),
        currency="RUB",
        payment_category="contract",
        author_sub="admin-sub",
    )
    sqlite_session.add(row)
    await sqlite_session.commit()
    await sqlite_session.refresh(row)
    return row
