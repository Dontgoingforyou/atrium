from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_finance.schemas.procurement import (
    PortalProcurementRequestCreate,
    PortalProcurementRequestRead,
    PortalProcurementRequestUpdate,
    ProcurementSummaryRead,
)
from app.portal_finance.services import procurement as svc

router = APIRouter(tags=["Закупки · Заявки"])


@router.get(
    "/procurement-summary",
    summary="Сводка по закупочным заявкам",
    description="Количество заявок по каждому статусу и суммарный бюджет. RBAC как у списка заявок.",
    response_model=ProcurementSummaryRead,
)
async def get_procurement_summary(
    user: CurrentUser,
    db: DbSession,
) -> ProcurementSummaryRead:
    return await svc.get_procurement_summary(db, user)


@router.get(
    "/procurement-requests",
    summary="Список закупочных заявок",
    description="Список заявок: все заявки видны всем авторизованным пользователям портала.",
    response_model=list[PortalProcurementRequestRead],
)
async def list_procurement_requests(
    user: CurrentUser,
    db: DbSession,
    status: str | None = Query(default=None, description="Фильтр по статусу"),
    counterparty_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[PortalProcurementRequestRead]:
    return await svc.list_procurement_requests(
        db,
        user,
        status=status,
        counterparty_id=counterparty_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/procurement-requests",
    summary="Создать закупочную заявку",
    description="Доступно пользователям с ролью «Закупщик» или администратору портала.",
    response_model=PortalProcurementRequestRead,
    status_code=201,
)
async def create_procurement_request(
    user: CurrentUser,
    db: DbSession,
    body: PortalProcurementRequestCreate,
) -> PortalProcurementRequestRead:
    return await svc.create_procurement_request(db, user, body)


@router.get(
    "/procurement-requests/{request_id}",
    summary="Карточка закупочной заявки",
    response_model=PortalProcurementRequestRead,
)
async def get_procurement_request(
    request_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalProcurementRequestRead:
    return await svc.get_procurement_request(db, user, request_id)


@router.patch(
    "/procurement-requests/{request_id}",
    summary="Обновить закупочную заявку",
    description="Автор или администратор портала.",
    response_model=PortalProcurementRequestRead,
)
async def update_procurement_request(
    request_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalProcurementRequestUpdate,
) -> PortalProcurementRequestRead:
    return await svc.update_procurement_request(db, user, request_id, body)


@router.delete(
    "/procurement-requests/{request_id}",
    summary="Отменить закупочную заявку",
    description="Soft-delete: устанавливает статус cancelled. Автор или администратор.",
    status_code=204,
)
async def delete_procurement_request(
    request_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await svc.delete_procurement_request(db, user, request_id)
