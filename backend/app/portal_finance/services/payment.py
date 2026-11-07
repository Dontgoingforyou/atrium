from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ContractStatus, InvoiceStatus
from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_finance import PortalContract, PortalInvoice, PortalPayment
from app.portal_finance.schemas.payment import FinanceSummaryRead, PortalPaymentCreate
from app.schemas.auth import UserPublic


def _ensure_can_delete_payment(user: UserPublic, row: PortalPayment) -> None:
    if user.is_portal_admin:
        return
    if row.author_sub != user.sub:
        raise ForbiddenError("Нет прав на удаление платежа")


async def list_payments(
    session: AsyncSession,
    user: UserPublic,
    *,
    invoice_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PortalPayment]:
    stmt = select(PortalPayment).options(selectinload(PortalPayment.invoice))
    if invoice_id is not None:
        stmt = stmt.where(PortalPayment.invoice_id == invoice_id)
    stmt = stmt.order_by(PortalPayment.created_at.desc()).limit(limit).offset(offset)
    return list((await session.scalars(stmt)).all())


async def create_payment(
    session: AsyncSession,
    user: UserPublic,
    data: PortalPaymentCreate,
) -> PortalPayment:
    if data.invoice_id is not None:
        invoice = await session.get(PortalInvoice, data.invoice_id)
        if invoice is None:
            raise NotFoundError("Счёт не найден")
    row = PortalPayment(
        invoice_id=data.invoice_id,
        amount=data.amount,
        currency=data.currency,
        paid_at=data.paid_at,
        note=data.note,
        payment_category=data.payment_category.value,
        author_sub=user.sub,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    await session.refresh(row, ["invoice"])
    return row


async def delete_payment(
    session: AsyncSession,
    user: UserPublic,
    payment_id: uuid.UUID,
) -> None:
    row = await session.get(PortalPayment, payment_id)
    if row is None:
        raise NotFoundError("Платёж не найден")
    _ensure_can_delete_payment(user, row)
    await session.delete(row)
    await session.commit()


async def get_finance_summary(
    session: AsyncSession,
    user: UserPublic,
) -> FinanceSummaryRead:
    """Агрегированные показатели: договоры, счета, платежи.

    Финансовые объекты глобально видимы всем авторизованным пользователям (без RBAC-фильтрации).
    Возвращает Pydantic-схему напрямую: нет соответствующего ORM-объекта (агрегат нескольких таблиц).
    """
    # Договоры
    ct_total, ct_active = (
        await session.execute(
            select(
                sa_func.count(PortalContract.id),
                sa_func.count(PortalContract.id).filter(PortalContract.status == ContractStatus.ACTIVE.value),
            ).select_from(PortalContract)
        )
    ).one()

    # Счета
    inv_total, inv_paid, inv_overdue = (
        await session.execute(
            select(
                sa_func.count(PortalInvoice.id),
                sa_func.count(PortalInvoice.id).filter(PortalInvoice.status == InvoiceStatus.PAID.value),
                sa_func.count(PortalInvoice.id).filter(PortalInvoice.status == InvoiceStatus.OVERDUE.value),
            ).select_from(PortalInvoice)
        )
    ).one()

    # Платежи
    pay_amount, pay_count = (
        await session.execute(
            select(
                sa_func.coalesce(sa_func.sum(PortalPayment.amount), Decimal("0")),
                sa_func.count(PortalPayment.id),
            ).select_from(PortalPayment)
        )
    ).one()

    return FinanceSummaryRead(
        contracts_total=int(ct_total),
        contracts_active=int(ct_active),
        invoices_total=int(inv_total),
        invoices_paid=int(inv_paid),
        invoices_overdue=int(inv_overdue),
        payments_total_amount=Decimal(pay_amount),
        payments_count=int(pay_count),
    )
