from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_finance import PortalInvoice
from app.portal_finance.schemas.invoice import PortalInvoiceCreate, PortalInvoiceRead, PortalInvoiceUpdate
from app.portal_finance.services.contract import get_contract
from app.schemas.auth import UserPublic


def _ensure_can_modify_invoice(user: UserPublic, row: PortalInvoice) -> None:
    if user.is_portal_admin:
        return
    if row.author_sub != user.sub:
        raise ForbiddenError("Нет прав на изменение счёта")


async def list_invoices(
    session: AsyncSession,
    user: UserPublic,
    *,
    status: str | None = None,
    invoice_type: str | None = None,
    contract_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PortalInvoiceRead]:
    stmt = select(PortalInvoice).options(selectinload(PortalInvoice.contract))
    if status is not None:
        stmt = stmt.where(PortalInvoice.status == status)
    if invoice_type is not None:
        stmt = stmt.where(PortalInvoice.invoice_type == invoice_type)
    if contract_id is not None:
        stmt = stmt.where(PortalInvoice.contract_id == contract_id)
    stmt = stmt.order_by(PortalInvoice.created_at.desc()).limit(limit).offset(offset)
    rows = list((await session.scalars(stmt)).all())
    return [PortalInvoiceRead.model_validate(r) for r in rows]


async def get_invoice(
    session: AsyncSession,
    user: UserPublic,
    invoice_id: uuid.UUID,
) -> PortalInvoiceRead:
    stmt = select(PortalInvoice).options(selectinload(PortalInvoice.contract)).where(PortalInvoice.id == invoice_id)
    row = (await session.scalars(stmt)).one_or_none()
    if row is None:
        raise NotFoundError("Счёт не найден")
    return PortalInvoiceRead.model_validate(row)


async def create_invoice(
    session: AsyncSession,
    user: UserPublic,
    data: PortalInvoiceCreate,
) -> PortalInvoiceRead:
    if data.contract_id is not None:
        await get_contract(session, user, data.contract_id)
    row = PortalInvoice(
        title=data.title,
        contract_id=data.contract_id,
        invoice_type=data.invoice_type.value,
        amount=data.amount,
        currency=data.currency,
        issue_date=data.issue_date,
        due_date=data.due_date,
        status=data.status.value,
        author_sub=user.sub,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    await session.refresh(row, ["contract"])
    return PortalInvoiceRead.model_validate(row)


async def update_invoice(
    session: AsyncSession,
    user: UserPublic,
    invoice_id: uuid.UUID,
    data: PortalInvoiceUpdate,
) -> PortalInvoiceRead:
    row = await session.get(PortalInvoice, invoice_id)
    if row is None:
        raise NotFoundError("Счёт не найден")
    _ensure_can_modify_invoice(user, row)
    patch = data.model_dump(exclude_unset=True)
    if patch.get("contract_id") is not None:
        await get_contract(session, user, patch["contract_id"])
    for field, value in patch.items():
        if field in ("invoice_type", "status") and value is not None:
            setattr(row, field, value.value)
        else:
            setattr(row, field, value)
    row.updated_at = _now_utc()
    await session.commit()
    await session.refresh(row)
    await session.refresh(row, ["contract"])
    return PortalInvoiceRead.model_validate(row)
