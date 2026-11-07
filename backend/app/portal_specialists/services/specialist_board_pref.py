from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_user_specialist_board_pref import PortalUserSpecialistBoardPref
from app.portal_specialists.schemas.board import SpecialistBoardPrefRead, SpecialistBoardPrefWrite
from app.portal_specialists.services.board_shared import require_manager_or_admin
from app.schemas.auth import UserPublic


def _empty_read() -> SpecialistBoardPrefRead:
    return SpecialistBoardPrefRead(column_order=[], hidden_column_keys=[])


async def get_specialist_board_pref(session: AsyncSession, user: UserPublic) -> SpecialistBoardPrefRead:
    require_manager_or_admin(user)
    row = (
        await session.execute(
            select(PortalUserSpecialistBoardPref).where(PortalUserSpecialistBoardPref.user_sub == user.sub)
        )
    ).scalar_one_or_none()
    if row is None:
        return _empty_read()
    known = await _known_column_keys(session)
    return SpecialistBoardPrefRead(
        column_order=_filter_known_keys(list(row.column_order or []), known),
        hidden_column_keys=_filter_known_keys(list(row.hidden_column_keys or []), known),
    )


async def _known_column_keys(session: AsyncSession) -> set[str]:
    rows = (await session.execute(select(PortalSpecialistColumn.key))).scalars().all()
    return set(rows)


def _filter_known_keys(keys: list[str], known: set[str]) -> list[str]:
    """Сохраняет порядок; отбрасывает ключи удалённых колонок (устаревший pref)."""
    return [k for k in keys if k in known]


async def put_specialist_board_pref(
    session: AsyncSession,
    user: UserPublic,
    body: SpecialistBoardPrefWrite,
) -> SpecialistBoardPrefRead:
    require_manager_or_admin(user)
    known = await _known_column_keys(session)
    order = _filter_known_keys(list(body.column_order), known)
    hidden = _filter_known_keys(list(body.hidden_column_keys), known)

    row = (
        await session.execute(
            select(PortalUserSpecialistBoardPref).where(PortalUserSpecialistBoardPref.user_sub == user.sub)
        )
    ).scalar_one_or_none()

    if row is None:
        row = PortalUserSpecialistBoardPref(
            user_sub=user.sub,
            column_order=order,
            hidden_column_keys=hidden,
        )
        session.add(row)
    else:
        row.column_order = order
        row.hidden_column_keys = hidden

    await session.flush()
    await session.commit()
    await session.refresh(row)
    return SpecialistBoardPrefRead(
        column_order=list(row.column_order or []),
        hidden_column_keys=list(row.hidden_column_keys or []),
    )
