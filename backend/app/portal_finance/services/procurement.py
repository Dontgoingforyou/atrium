from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ProcurementStatus
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import is_manager_or_admin
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_finance import PortalProcurementRequest
from app.portal_finance.schemas.procurement import (
    PortalProcurementRequestCreate,
    PortalProcurementRequestRead,
    PortalProcurementRequestUpdate,
    ProcurementSummaryRead,
)
from app.portal_finance.services.counterparty import get_counterparty
from app.schemas.auth import UserPublic


def _has_procurement_role(user: UserPublic) -> bool:
    return is_manager_or_admin(user)


def _ensure_can_modify(user: UserPublic, row: PortalProcurementRequest) -> None:
    if user.is_portal_admin:
        return
    if row.author_sub != user.sub:
        raise ForbiddenError("Нет прав на изменение закупочной заявки")


async def list_procurement_requests(
    session: AsyncSession,
    user: UserPublic,
    *,
    status: str | None = None,
    counterparty_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PortalProcurementRequestRead]:
    stmt = select(PortalProcurementRequest).options(selectinload(PortalProcurementRequest.counterparty))
    if status is not None:
        stmt = stmt.where(PortalProcurementRequest.status == status)
    if counterparty_id is not None:
        stmt = stmt.where(PortalProcurementRequest.counterparty_id == counterparty_id)
    stmt = stmt.order_by(PortalProcurementRequest.created_at.desc()).limit(limit).offset(offset)
    rows = list((await session.scalars(stmt)).all())
    return [PortalProcurementRequestRead.model_validate(r) for r in rows]


async def get_procurement_request(
    session: AsyncSession,
    user: UserPublic,
    request_id: uuid.UUID,
) -> PortalProcurementRequestRead:
    stmt = (
        select(PortalProcurementRequest)
        .where(PortalProcurementRequest.id == request_id)
        .options(selectinload(PortalProcurementRequest.counterparty))
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Закупочная заявка не найдена")
    return PortalProcurementRequestRead.model_validate(row)


async def create_procurement_request(
    session: AsyncSession,
    user: UserPublic,
    data: PortalProcurementRequestCreate,
) -> PortalProcurementRequestRead:
    if not _has_procurement_role(user):
        raise ForbiddenError("Создание закупочных заявок доступно только пользователям с ролью «Закупщик»")
    if data.counterparty_id is not None:
        await get_counterparty(session, user, data.counterparty_id)
    row = PortalProcurementRequest(
        title=data.title,
        description=data.description,
        status=data.status.value,
        counterparty_id=data.counterparty_id,
        amount=data.amount,
        currency=data.currency,
        document_id=data.document_id,
        author_sub=user.sub,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row, ["counterparty"])
    return PortalProcurementRequestRead.model_validate(row)


async def update_procurement_request(
    session: AsyncSession,
    user: UserPublic,
    request_id: uuid.UUID,
    data: PortalProcurementRequestUpdate,
) -> PortalProcurementRequestRead:
    stmt = (
        select(PortalProcurementRequest)
        .where(PortalProcurementRequest.id == request_id)
        .options(selectinload(PortalProcurementRequest.counterparty))
    )
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Закупочная заявка не найдена")
    _ensure_can_modify(user, row)
    patch = data.model_dump(exclude_unset=True)
    if patch.get("counterparty_id") is not None:
        await get_counterparty(session, user, patch["counterparty_id"])
    for field, value in patch.items():
        if field == "status" and value is not None:
            setattr(row, field, value.value)
        else:
            setattr(row, field, value)
    row.updated_at = _now_utc()
    await session.commit()
    await session.refresh(row, ["counterparty"])
    return PortalProcurementRequestRead.model_validate(row)


async def delete_procurement_request(
    session: AsyncSession,
    user: UserPublic,
    request_id: uuid.UUID,
) -> None:
    """Soft-delete: устанавливает статус cancelled."""
    row = await session.get(PortalProcurementRequest, request_id)
    if row is None:
        raise NotFoundError("Закупочная заявка не найдена")
    _ensure_can_modify(user, row)
    row.status = ProcurementStatus.CANCELLED.value
    row.updated_at = _now_utc()
    await session.commit()


async def get_procurement_summary(
    session: AsyncSession,
    user: UserPublic,
) -> ProcurementSummaryRead:
    """Агрегат: количество заявок по статусам и суммарный бюджет."""
    stmt = select(
        PortalProcurementRequest.status,
        func.count().label("cnt"),
        func.coalesce(func.sum(PortalProcurementRequest.amount), Decimal("0")).label("budget_sum"),
    ).group_by(PortalProcurementRequest.status)
    rows = (await session.execute(stmt)).all()
    by_status: dict[str, int] = {r.status: r.cnt for r in rows}
    total = sum(by_status.values())
    total_budget: Decimal = sum((r.budget_sum or Decimal("0") for r in rows), Decimal("0"))
    return ProcurementSummaryRead(total=total, by_status=by_status, total_budget=total_budget)
