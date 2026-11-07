"""Домашний экран: блок «Мои задачи»."""

from __future__ import annotations

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_task import PortalTask
from app.portal_collab.services._task_home_common import (
    _home_my_tasks_order_by,
    _is_overdue_expr,
)
from app.portal_collab.services.task import _apply_list_tasks_filters
from app.portal_collab.services.task_column import apply_kpi_active_filter
from app.schemas.auth import UserPublic

# ── «Мои задачи» ─────────────────────────────────────────────────────────────


async def list_my_tasks_home_preview(
    session: AsyncSession,
    user: UserPublic,
    *,
    limit: int,
    kpi_excluded: frozenset[str],
    closed_statuses: frozenset[str] | None = None,
) -> list[PortalTask]:
    """Все «мои» задачи (любой статус), сортировка: KPI-активные и просроченные выше."""
    now = _now_utc()
    stmt = _apply_list_tasks_filters(
        select(PortalTask).options(selectinload(PortalTask.tags)),
        user,
        mine_only=True,
    )
    stmt = stmt.order_by(*_home_my_tasks_order_by(now, kpi_excluded, closed_statuses)).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def count_my_tasks_home_summary(
    session: AsyncSession,
    user: UserPublic,
    *,
    kpi_excluded: frozenset[str],
    closed_statuses: frozenset[str] | None = None,
) -> tuple[int, int]:
    """Число KPI-активных и просроченных «моих» задач."""
    now = _now_utc()
    base = apply_kpi_active_filter(
        _apply_list_tasks_filters(select(PortalTask), user, mine_only=True),
        kpi_excluded,
    )
    open_count = int(await session.scalar(select(sa_func.count()).select_from(base.subquery())) or 0)
    overdue_base = base.where(_is_overdue_expr(now, kpi_excluded, closed_statuses))
    overdue_count = int(await session.scalar(select(sa_func.count()).select_from(overdue_base.subquery())) or 0)
    return open_count, overdue_count
