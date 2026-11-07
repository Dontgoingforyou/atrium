from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_finance.schemas.invoice import PortalInvoiceCreate, PortalInvoiceRead, PortalInvoiceUpdate
from app.portal_finance.services import invoice as svc

router = APIRouter(tags=["Финансы · Счета и акты"])


@router.get(
    "/invoices",
    summary="Список счетов и актов",
    response_model=list[PortalInvoiceRead],
)
async def list_invoices(
    user: CurrentUser,
    db: DbSession,
    status: str | None = Query(default=None),
    invoice_type: str | None = Query(default=None, description="invoice | act"),
    contract_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[PortalInvoiceRead]:
    return await svc.list_invoices(
        db,
        user,
        status=status,
        invoice_type=invoice_type,
        contract_id=contract_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/invoices",
    summary="Создать счёт или акт",
    response_model=PortalInvoiceRead,
    status_code=201,
)
async def create_invoice(
    user: CurrentUser,
    db: DbSession,
    body: PortalInvoiceCreate,
) -> PortalInvoiceRead:
    return await svc.create_invoice(db, user, body)


@router.get(
    "/invoices/{invoice_id}",
    summary="Карточка счёта / акта",
    response_model=PortalInvoiceRead,
)
async def get_invoice(
    invoice_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalInvoiceRead:
    return await svc.get_invoice(db, user, invoice_id)


@router.patch(
    "/invoices/{invoice_id}",
    summary="Обновить счёт / акт",
    description="Автор или администратор.",
    response_model=PortalInvoiceRead,
)
async def update_invoice(
    invoice_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalInvoiceUpdate,
) -> PortalInvoiceRead:
    return await svc.update_invoice(db, user, invoice_id, body)
