from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_finance import PortalCounterparty
from app.portal_finance.schemas.counterparty import (
    PortalCounterpartyCreate,
    PortalCounterpartyRead,
    PortalCounterpartyUpdate,
)
from app.schemas.auth import UserPublic


def _require_admin(user: UserPublic) -> None:
    if not user.is_portal_admin:
        raise ForbiddenError("Только администратор портала может управлять контрагентами")


async def list_counterparties(
    session: AsyncSession,
    user: UserPublic,
    *,
    limit: int = 100,
    offset: int = 0,
) -> list[PortalCounterpartyRead]:
    stmt = select(PortalCounterparty).order_by(PortalCounterparty.name)
    if not user.is_portal_admin:
        stmt = stmt.where(PortalCounterparty.is_active.is_(True))
    stmt = stmt.limit(limit).offset(offset)
    rows = list((await session.scalars(stmt)).all())
    return [PortalCounterpartyRead.model_validate(r) for r in rows]


async def get_counterparty(
    session: AsyncSession,
    user: UserPublic,
    counterparty_id: uuid.UUID,
) -> PortalCounterpartyRead:
    row = await session.get(PortalCounterparty, counterparty_id)
    if row is None:
        raise NotFoundError("Контрагент не найден")
    if not user.is_portal_admin and not row.is_active:
        raise NotFoundError("Контрагент не найден")
    return PortalCounterpartyRead.model_validate(row)


async def create_counterparty(
    session: AsyncSession,
    user: UserPublic,
    data: PortalCounterpartyCreate,
) -> PortalCounterpartyRead:
    _require_admin(user)
    row = PortalCounterparty(
        name=data.name,
        inn=data.inn,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        counterparty_type=data.counterparty_type.value,
        note=data.note,
        is_active=data.is_active,
        author_sub=user.sub,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return PortalCounterpartyRead.model_validate(row)


async def update_counterparty(
    session: AsyncSession,
    user: UserPublic,
    counterparty_id: uuid.UUID,
    data: PortalCounterpartyUpdate,
) -> PortalCounterpartyRead:
    _require_admin(user)
    row = await session.get(PortalCounterparty, counterparty_id)
    if row is None:
        raise NotFoundError("Контрагент не найден")
    patch = data.model_dump(exclude_unset=True)
    for field, value in patch.items():
        if field == "counterparty_type" and value is not None:
            setattr(row, field, value.value)
        else:
            setattr(row, field, value)
    row.updated_at = _now_utc()
    await session.commit()
    await session.refresh(row)
    return PortalCounterpartyRead.model_validate(row)
