from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_finance.schemas.payment import FinanceSummaryRead, PortalPaymentCreate, PortalPaymentRead
from app.portal_finance.services import payment as svc

router = APIRouter(tags=["Финансы · Платежи"])


@router.get(
    "/summary",
    summary="Финансовый KPI-агрегат",
    description="Счётчики и суммы по договорам, счетам и платежам. Глобально видимы всем авторизованным.",
    response_model=FinanceSummaryRead,
    tags=["Финансы · Отчёты"],
)
async def finance_summary(
    user: CurrentUser,
    db: DbSession,
) -> FinanceSummaryRead:
    return await svc.get_finance_summary(db, user)


@router.get(
    "/payments",
    summary="Список платежей",
    response_model=list[PortalPaymentRead],
)
async def list_payments(
    user: CurrentUser,
    db: DbSession,
    invoice_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[PortalPaymentRead]:
    rows = await svc.list_payments(db, user, invoice_id=invoice_id, limit=limit, offset=offset)
    return [PortalPaymentRead.model_validate(r) for r in rows]


@router.post(
    "/payments",
    summary="Зарегистрировать платёж",
    response_model=PortalPaymentRead,
    status_code=201,
)
async def create_payment(
    user: CurrentUser,
    db: DbSession,
    body: PortalPaymentCreate,
) -> PortalPaymentRead:
    payment = await svc.create_payment(db, user, body)
    return PortalPaymentRead.model_validate(payment)


@router.delete(
    "/payments/{payment_id}",
    summary="Удалить платёж",
    description="Автор или администратор.",
    status_code=204,
)
async def delete_payment(
    payment_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await svc.delete_payment(db, user, payment_id)
