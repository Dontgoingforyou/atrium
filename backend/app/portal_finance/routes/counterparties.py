from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_finance.schemas.counterparty import (
    PortalCounterpartyCreate,
    PortalCounterpartyRead,
    PortalCounterpartyUpdate,
)
from app.portal_finance.services import counterparty as svc

router = APIRouter(tags=["Финансы · Контрагенты"])


@router.get(
    "/counterparties",
    summary="Список контрагентов",
    description="Обычный пользователь видит только активных контрагентов. Администратор — всех.",
    response_model=list[PortalCounterpartyRead],
)
async def list_counterparties(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[PortalCounterpartyRead]:
    return await svc.list_counterparties(db, user, limit=limit, offset=offset)


@router.post(
    "/counterparties",
    summary="Создать контрагента",
    description="Только для администратора портала.",
    response_model=PortalCounterpartyRead,
    status_code=201,
)
async def create_counterparty(
    user: CurrentUser,
    db: DbSession,
    body: PortalCounterpartyCreate,
) -> PortalCounterpartyRead:
    return await svc.create_counterparty(db, user, body)


@router.get(
    "/counterparties/{counterparty_id}",
    summary="Карточка контрагента",
    response_model=PortalCounterpartyRead,
)
async def get_counterparty(
    counterparty_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalCounterpartyRead:
    return await svc.get_counterparty(db, user, counterparty_id)


@router.patch(
    "/counterparties/{counterparty_id}",
    summary="Обновить контрагента",
    description="Только для администратора портала.",
    response_model=PortalCounterpartyRead,
)
async def update_counterparty(
    counterparty_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalCounterpartyUpdate,
) -> PortalCounterpartyRead:
    return await svc.update_counterparty(db, user, counterparty_id, body)
