from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import ContractStatus
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_finance import PortalContract
from app.portal_finance.schemas.contract import PortalContractCreate, PortalContractRead, PortalContractUpdate
from app.portal_finance.services.counterparty import get_counterparty
from app.schemas.auth import UserPublic


def _ensure_can_modify_contract(user: UserPublic, row: PortalContract) -> None:
    if user.is_portal_admin:
        return
    if row.author_sub != user.sub:
        raise ForbiddenError("Нет прав на изменение договора")


def _with_profiles(stmt: Any) -> Any:
    return stmt.options(
        selectinload(PortalContract.counterparty),
        selectinload(PortalContract.author_profile),
        selectinload(PortalContract.owner_profile),
    )


async def list_contracts(
    session: AsyncSession,
    user: UserPublic,
    *,
    status: str | None = None,
    contract_type: str | None = None,
    counterparty_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PortalContractRead]:
    stmt = _with_profiles(select(PortalContract))
    if status is not None:
        stmt = stmt.where(PortalContract.status == status)
    if contract_type is not None:
        stmt = stmt.where(PortalContract.contract_type == contract_type)
    if counterparty_id is not None:
        stmt = stmt.where(PortalContract.counterparty_id == counterparty_id)
    stmt = stmt.order_by(PortalContract.created_at.desc()).limit(limit).offset(offset)
    rows = list((await session.scalars(stmt)).all())
    return [PortalContractRead.model_validate(r) for r in rows]


async def get_contract(
    session: AsyncSession,
    user: UserPublic,
    contract_id: uuid.UUID,
) -> PortalContractRead:
    stmt = _with_profiles(select(PortalContract)).where(PortalContract.id == contract_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Договор не найден")
    return PortalContractRead.model_validate(row)


async def create_contract(
    session: AsyncSession,
    user: UserPublic,
    data: PortalContractCreate,
) -> PortalContractRead:
    if data.counterparty_id is not None:
        await get_counterparty(session, user, data.counterparty_id)
    effective_owner = data.owner_sub if user.is_portal_admin and data.owner_sub else user.sub
    row = PortalContract(
        title=data.title,
        contract_type=data.contract_type.value,
        counterparty_id=data.counterparty_id,
        amount=data.amount,
        currency=data.currency,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status.value,
        document_id=data.document_id,
        author_sub=user.sub,
        owner_sub=effective_owner,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row, ["counterparty", "author_profile", "owner_profile"])
    return PortalContractRead.model_validate(row)


async def update_contract(
    session: AsyncSession,
    user: UserPublic,
    contract_id: uuid.UUID,
    data: PortalContractUpdate,
) -> PortalContractRead:
    stmt = _with_profiles(select(PortalContract)).where(PortalContract.id == contract_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise NotFoundError("Договор не найден")
    _ensure_can_modify_contract(user, row)
    patch = data.model_dump(exclude_unset=True)
    if not user.is_portal_admin:
        patch.pop("owner_sub", None)
    if patch.get("counterparty_id") is not None:
        await get_counterparty(session, user, patch["counterparty_id"])
    for field, value in patch.items():
        if field in ("contract_type", "status") and value is not None:
            setattr(row, field, value.value)
        else:
            setattr(row, field, value)
    row.updated_at = _now_utc()
    await session.commit()
    await session.refresh(row, ["counterparty", "author_profile", "owner_profile"])
    return PortalContractRead.model_validate(row)


async def delete_contract(
    session: AsyncSession,
    user: UserPublic,
    contract_id: uuid.UUID,
) -> None:
    """Soft-delete: устанавливает статус cancelled."""
    row = await session.get(PortalContract, contract_id)
    if row is None:
        raise NotFoundError("Договор не найден")
    _ensure_can_modify_contract(user, row)
    row.status = ContractStatus.CANCELLED.value
    row.updated_at = _now_utc()
    await session.commit()
