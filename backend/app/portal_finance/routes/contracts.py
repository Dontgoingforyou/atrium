from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_finance.schemas.contract import PortalContractCreate, PortalContractRead, PortalContractUpdate
from app.portal_finance.services import contract as svc

router = APIRouter(tags=["Финансы · Договоры"])


@router.get(
    "/contracts",
    summary="Список договоров",
    description="Список договоров: все договоры видны всем авторизованным пользователям портала.",
    response_model=list[PortalContractRead],
)
async def list_contracts(
    user: CurrentUser,
    db: DbSession,
    status: str | None = Query(default=None, description="Фильтр по статусу"),
    contract_type: str | None = Query(default=None, description="Фильтр по типу"),
    counterparty_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[PortalContractRead]:
    return await svc.list_contracts(
        db,
        user,
        status=status,
        contract_type=contract_type,
        counterparty_id=counterparty_id,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/contracts",
    summary="Создать договор",
    response_model=PortalContractRead,
    status_code=201,
)
async def create_contract(
    user: CurrentUser,
    db: DbSession,
    body: PortalContractCreate,
) -> PortalContractRead:
    return await svc.create_contract(db, user, body)


@router.get(
    "/contracts/{contract_id}",
    summary="Карточка договора",
    response_model=PortalContractRead,
)
async def get_contract(
    contract_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalContractRead:
    return await svc.get_contract(db, user, contract_id)


@router.patch(
    "/contracts/{contract_id}",
    summary="Обновить договор",
    description="Автор или администратор портала.",
    response_model=PortalContractRead,
)
async def update_contract(
    contract_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalContractUpdate,
) -> PortalContractRead:
    return await svc.update_contract(db, user, contract_id, body)


@router.delete(
    "/contracts/{contract_id}",
    summary="Отменить договор",
    description="Soft-delete: устанавливает статус cancelled. Автор или администратор.",
    status_code=204,
)
async def delete_contract(
    contract_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await svc.delete_contract(db, user, contract_id)
