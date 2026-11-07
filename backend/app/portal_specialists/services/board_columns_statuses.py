"""Колонки воронки и направления (статусы) специалистов."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_specialist_status import PortalSpecialistStatus
from app.portal_specialists.schemas.board import (
    SpecialistColumnCreate,
    SpecialistColumnUpdate,
    SpecialistStatusCreate,
    SpecialistStatusUpdate,
)
from app.portal_specialists.services.board_shared import require_manager_or_admin
from app.schemas.auth import UserPublic


async def list_specialist_columns(
    session: AsyncSession,
    user: UserPublic,
) -> list[PortalSpecialistColumn]:
    """Список колонок воронки специалистов (глобальный справочник)."""
    require_manager_or_admin(user)
    stmt = select(PortalSpecialistColumn).order_by(PortalSpecialistColumn.position)
    return list((await session.execute(stmt)).scalars().all())


async def create_specialist_column(
    session: AsyncSession,
    user: UserPublic,
    data: SpecialistColumnCreate,
) -> PortalSpecialistColumn:
    """Создать колонку воронки. Только администратор портала."""
    if not user.is_portal_admin:
        raise ForbiddenError("Создание колонок воронки — только для администратора портала")
    col = PortalSpecialistColumn(
        key=data.key,
        title=data.title,
        color=data.color,
        position=data.position,
    )
    session.add(col)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError(f"Колонка с ключом «{data.key}» уже существует") from e
    await session.refresh(col)
    return col


async def update_specialist_column(
    session: AsyncSession,
    user: UserPublic,
    col_id: uuid.UUID,
    data: SpecialistColumnUpdate,
) -> PortalSpecialistColumn:
    """Обновить колонку воронки. Только администратор портала."""
    if not user.is_portal_admin:
        raise ForbiddenError("Редактирование колонок воронки — только для администратора портала")
    col = await session.get(PortalSpecialistColumn, col_id)
    if col is None:
        raise NotFoundError("Колонка не найдена")
    if data.title is not None:
        col.title = data.title
    if data.color is not None:
        col.color = data.color
    if data.position is not None:
        col.position = data.position
    await session.commit()
    await session.refresh(col)
    return col


async def delete_specialist_column(
    session: AsyncSession,
    user: UserPublic,
    col_id: uuid.UUID,
) -> None:
    """Удалить колонку воронки. Только администратор портала."""
    if not user.is_portal_admin:
        raise ForbiddenError("Удаление колонок воронки — только для администратора портала")
    col = await session.get(PortalSpecialistColumn, col_id)
    if col is None:
        raise NotFoundError("Колонка не найдена")
    entry_count: int = (
        await session.scalar(
            select(func.count())
            .select_from(PortalManagerSpecialist)
            .where(PortalManagerSpecialist.column_key == col.key),
        )
        or 0
    )
    if entry_count > 0:
        raise ConflictError(
            f"Нельзя удалить колонку: на доске {entry_count} "
            f"{'закрепление' if entry_count == 1 else 'закрепления' if 2 <= entry_count <= 4 else 'закреплений'}. "
            "Сначала переместите или снимите специалистов с доски."
        )
    await session.delete(col)
    await session.commit()


async def list_specialist_statuses(
    session: AsyncSession,
    user: UserPublic,
) -> list[PortalSpecialistStatus]:
    """Список статусов специалистов (глобальный справочник)."""
    require_manager_or_admin(user)
    stmt = select(PortalSpecialistStatus).order_by(PortalSpecialistStatus.title)
    return list((await session.execute(stmt)).scalars().all())


async def create_specialist_status(
    session: AsyncSession,
    user: UserPublic,
    data: SpecialistStatusCreate,
) -> PortalSpecialistStatus:
    """Создать статус. Любой менеджер или администратор (как создание тегов)."""
    require_manager_or_admin(user)
    status = PortalSpecialistStatus(title=data.title.strip(), color=data.color)
    session.add(status)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError(f"Статус «{data.title.strip()}» уже существует") from e
    await session.refresh(status)
    return status


async def update_specialist_status(
    session: AsyncSession,
    user: UserPublic,
    status_id: uuid.UUID,
    data: SpecialistStatusUpdate,
) -> PortalSpecialistStatus:
    """Обновить статус. Только администратор портала."""
    if not user.is_portal_admin:
        raise ForbiddenError("Редактирование статусов — только для администратора портала")
    status = await session.get(PortalSpecialistStatus, status_id)
    if status is None:
        raise NotFoundError("Статус не найден")
    if data.title is not None:
        status.title = data.title.strip()
    if data.color is not None:
        status.color = data.color
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise ConflictError("Статус с таким названием уже существует") from e
    await session.refresh(status)
    return status


async def delete_specialist_status(
    session: AsyncSession,
    user: UserPublic,
    status_id: uuid.UUID,
) -> None:
    """Удалить статус. Только администратор портала.

    Записи на доске, использующие этот статус, получат status_id = NULL (ON DELETE SET NULL).
    """
    if not user.is_portal_admin:
        raise ForbiddenError("Удаление статусов — только для администратора портала")
    status = await session.get(PortalSpecialistStatus, status_id)
    if status is None:
        raise NotFoundError("Статус не найден")
    await session.delete(status)
    await session.commit()
