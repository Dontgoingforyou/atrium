from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import TaskStatus
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import is_manager_or_admin
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskColumn
from app.portal_collab.schemas.task import PortalTaskColumnCreate, PortalTaskColumnUpdate
from app.portal_collab.services._task_home_common import (
    is_approval_like_column_title,
    is_cancelled_like_column_title,
    is_done_like_column_title,
)
from app.portal_collab.services.task_jira_column_sync import bind_column_jira_status_by_title
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TaskColumnStatusSets:
    """Ключи колонок по семантике title: один select на все KPI/фильтры."""

    done_like: frozenset[str]
    approval_like: frozenset[str]
    cancelled_like: frozenset[str]
    closed: frozenset[str]
    kpi_inactive: frozenset[str]


def _require_can_manage_columns(user: UserPublic) -> None:
    if not (user.is_portal_admin or is_manager_or_admin(user)):
        raise ForbiddenError("Управление колонками канбана доступно только администраторам и руководителям")


def _classify_column_status_sets(
    rows: list[tuple[str, str, bool]],
) -> TaskColumnStatusSets:
    done_like: set[str] = set()
    approval_like: set[str] = set()
    cancelled_like: set[str] = set()
    flagged: set[str] = set()
    known_keys: set[str] = set()
    for status_key, title, exclude_from_kpi in rows:
        key = str(status_key)
        known_keys.add(key)
        if exclude_from_kpi:
            flagged.add(key)
        heading = str(title).strip() if title else ""
        if not heading:
            continue
        if is_done_like_column_title(heading):
            done_like.add(key)
        elif is_approval_like_column_title(heading):
            approval_like.add(key)
        elif is_cancelled_like_column_title(heading):
            cancelled_like.add(key)
    closed = {TaskStatus.CANCELLED.value} | done_like | approval_like | cancelled_like
    # Нет колонки с ключом done — enum «Готово» остаётся закрытым (тесты / пустая доска).
    if TaskStatus.DONE.value not in known_keys:
        closed.add(TaskStatus.DONE.value)
    return TaskColumnStatusSets(
        done_like=frozenset(done_like),
        approval_like=frozenset(approval_like),
        cancelled_like=frozenset(cancelled_like),
        closed=frozenset(closed),
        kpi_inactive=frozenset(closed | flagged),
    )


async def task_column_status_sets(session: AsyncSession) -> TaskColumnStatusSets:
    """Один select: done-like / approval-like / closed / kpi_inactive (closed ∪ флаг)."""
    stmt = select(
        PortalTaskColumn.status_key,
        PortalTaskColumn.title,
        PortalTaskColumn.exclude_from_kpi,
    )
    rows = [
        (str(status_key), str(title) if title is not None else "", bool(exclude_from_kpi))
        for status_key, title, exclude_from_kpi in (await session.execute(stmt)).all()
    ]
    return _classify_column_status_sets(rows)


async def kpi_excluded_status_keys(session: AsyncSession) -> frozenset[str]:
    """Статусы вне open KPI: закрытые колонки ∪ ``exclude_from_kpi``."""
    return (await task_column_status_sets(session)).kpi_inactive


async def closed_task_status_keys(session: AsyncSession) -> frozenset[str]:
    """Закрытые статусы: done-like ∪ approval-like ∪ cancelled (и enum done, если колонки нет)."""
    return (await task_column_status_sets(session)).closed


async def done_like_status_keys(session: AsyncSession) -> frozenset[str]:
    """Ключи колонок «Готово» для чипа «Завершена» — не «На согласовании» даже при ``status_key=done``."""
    return (await task_column_status_sets(session)).done_like


def apply_kpi_active_filter(stmt: Any, kpi_excluded: frozenset[str]) -> Any:
    """Оставить только задачи, участвующие в KPI (status не в исключённых ключах)."""
    if kpi_excluded:
        stmt = stmt.where(PortalTask.status.not_in(kpi_excluded))
    return stmt


async def list_known_task_status_keys(session: AsyncSession) -> frozenset[str]:
    """Все status_key существующих колонок канбана (единый глобальный скоуп)."""
    stmt = select(PortalTaskColumn.status_key)
    rows = (await session.execute(stmt)).scalars().all()
    return frozenset(str(k) for k in rows)


async def assert_valid_task_status(session: AsyncSession, status_key: str) -> None:
    """Проверить, что status_key соответствует существующей колонке канбана."""
    known = await list_known_task_status_keys(session)
    if not known:
        return
    if status_key not in known:
        raise ConflictError(f"Неизвестный статус задачи: {status_key}")


async def list_task_columns(session: AsyncSession, user: UserPublic) -> list[PortalTaskColumn]:
    """Вернуть все колонки канбана (единый глобальный скоуп)."""
    stmt = select(PortalTaskColumn).order_by(PortalTaskColumn.position)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_task_column(
    session: AsyncSession,
    user: UserPublic,
    data: PortalTaskColumnCreate,
    *,
    http: httpx.AsyncClient | None = None,
) -> PortalTaskColumn:
    _require_can_manage_columns(user)
    exclude_from_kpi = data.exclude_from_kpi if user.is_portal_admin else False
    column = PortalTaskColumn(
        title=data.title,
        color=data.color,
        status_key=data.status_key,
        position=data.position,
        exclude_from_kpi=exclude_from_kpi,
    )
    session.add(column)
    await session.flush()
    if http is not None:
        await bind_column_jira_status_by_title(column, http)
    await session.commit()
    await session.refresh(column)
    return column


async def update_task_column(
    session: AsyncSession,
    user: UserPublic,
    column_id: uuid.UUID,
    data: PortalTaskColumnUpdate,
    *,
    http: httpx.AsyncClient | None = None,
) -> PortalTaskColumn:
    _require_can_manage_columns(user)
    column = await session.get(PortalTaskColumn, column_id)
    if column is None:
        raise NotFoundError("Колонка не найдена")
    if data.exclude_from_kpi is not None:
        if not user.is_portal_admin:
            logger.warning(
                "Отказ в смене exclude_from_kpi: user_sub=%s column_id=%s",
                user.sub,
                column_id,
            )
            raise ForbiddenError("Исключение колонки из KPI доступно только администратору портала")
        column.exclude_from_kpi = data.exclude_from_kpi
    title_changed = False
    if data.title is not None:
        title_changed = data.title != column.title
        column.title = data.title
    if data.color is not None:
        column.color = data.color
    if data.position is not None:
        column.position = data.position
    if data.jira_status_id is not None:
        if not user.is_portal_admin:
            raise ForbiddenError("Привязка jira_status_id доступна только администратору портала")
        column.jira_status_id = data.jira_status_id.strip() or None
    elif title_changed and http is not None:
        await bind_column_jira_status_by_title(column, http)
    await session.flush()
    await session.commit()
    await session.refresh(column)
    return column


async def delete_task_column(
    session: AsyncSession,
    user: UserPublic,
    column_id: uuid.UUID,
) -> None:
    _require_can_manage_columns(user)
    column = await session.get(PortalTaskColumn, column_id)
    if column is None:
        raise NotFoundError("Колонка не найдена")
    task_count: int = (
        await session.scalar(select(func.count()).select_from(PortalTask).where(PortalTask.status == column.status_key))
        or 0
    )
    if task_count > 0:
        raise ConflictError(
            f"Нельзя удалить колонку: в ней {task_count} "
            f"{'задача' if task_count == 1 else 'задачи' if 2 <= task_count <= 4 else 'задач'}. "
            "Сначала переместите или закройте все задачи."
        )
    await session.delete(column)
    await session.commit()
