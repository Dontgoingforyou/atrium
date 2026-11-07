"""Домашний экран: команда администратора портала."""

from __future__ import annotations

from typing import Any

from sqlalchemy import case, select
from sqlalchemy import func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import TaskStatus
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.services._task_due_calendar import overdue_cutoff_utc
from app.portal_collab.services._task_home_common import (
    HOME_ASSIGNEE_LOAD_LIMIT,
    _avatar_url_from_profile,
    _empty_open_priority_counts,
    _home_kpi_task_order_by,
    _is_overdue_expr,
    apply_done_this_month_filter,
    apply_no_assignee_filter,
)
from app.portal_collab.services.task import _apply_list_tasks_filters
from app.portal_collab.services.task_column import apply_kpi_active_filter, closed_task_status_keys
from app.schemas.auth import UserPublic

# ── Команда (администратор портала) ──────────────────────────────────────────


async def list_admin_team_tasks_home_preview(
    session: AsyncSession,
    user: UserPublic,
    *,
    limit: int,
    kpi_excluded: frozenset[str],
    closed_statuses: frozenset[str] | None = None,
) -> list[PortalTask]:
    """KPI-активные задачи команды для администратора портала."""
    if not user.is_portal_admin:
        return []
    now = _now_utc()
    stmt = _apply_list_tasks_filters(
        select(PortalTask).options(selectinload(PortalTask.tags)),
        user,
        mine_only=False,
    )
    stmt = apply_kpi_active_filter(stmt, kpi_excluded)
    stmt = stmt.order_by(*_home_kpi_task_order_by(now, kpi_excluded, closed_statuses)).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def count_admin_team_tasks_home_summary(
    session: AsyncSession,
    user: UserPublic,
    *,
    kpi_excluded: frozenset[str],
    closed_statuses: frozenset[str] | None = None,
) -> tuple[int, int]:
    """Счётчики KPI-активных и просроченных задач команды."""
    if not user.is_portal_admin:
        return 0, 0
    now = _now_utc()
    base = apply_kpi_active_filter(
        _apply_list_tasks_filters(select(PortalTask), user, mine_only=False),
        kpi_excluded,
    )
    open_count = int(await session.scalar(select(sa_func.count()).select_from(base.subquery())) or 0)
    overdue_base = base.where(_is_overdue_expr(now, kpi_excluded, closed_statuses))
    overdue_count = int(await session.scalar(select(sa_func.count()).select_from(overdue_base.subquery())) or 0)
    return open_count, overdue_count


async def count_admin_team_open_tasks_by_priority(
    session: AsyncSession,
    user: UserPublic,
    *,
    kpi_excluded: frozenset[str],
) -> dict[str, int]:
    """KPI-активные задачи команды по приоритету."""
    if not user.is_portal_admin:
        return _empty_open_priority_counts()
    subq = apply_kpi_active_filter(
        _apply_list_tasks_filters(
            select(PortalTask.priority),
            user,
            mine_only=False,
        ),
        kpi_excluded,
    ).subquery()
    stmt = select(subq.c.priority, sa_func.count()).select_from(subq).group_by(subq.c.priority)
    rows = (await session.execute(stmt)).all()
    out = _empty_open_priority_counts()
    for pr, cnt in rows:
        k = str(pr)
        if k in out:
            out[k] = int(cnt)
    return out


async def count_admin_team_done_this_month(session: AsyncSession, user: UserPublic) -> int:
    """Задачи команды, закрытые (Готово + На согласовании + отмена) с начала месяца портала."""
    if not user.is_portal_admin:
        return 0
    closed = await closed_task_status_keys(session)
    base = apply_done_this_month_filter(
        _apply_list_tasks_filters(select(PortalTask), user, mine_only=False),
        closed,
    )
    return int(await session.scalar(select(sa_func.count()).select_from(base.subquery())) or 0)


async def count_admin_team_no_assignee(
    session: AsyncSession,
    user: UserPublic,
    *,
    kpi_excluded: frozenset[str],
) -> int:
    """KPI-активные задачи команды без исполнителя (ни колонка, ни junction)."""
    if not user.is_portal_admin:
        return 0
    base = apply_kpi_active_filter(
        apply_no_assignee_filter(_apply_list_tasks_filters(select(PortalTask), user, mine_only=False)),
        kpi_excluded,
    )
    return int(await session.scalar(select(sa_func.count()).select_from(base.subquery())) or 0)


async def count_admin_team_tasks_by_status(
    session: AsyncSession,
    user: UserPublic,
    *,
    kpi_excluded: frozenset[str],
) -> dict[str, int]:
    """KPI-активные задачи команды с разбивкой по статусам (todo / in_progress)."""
    if not user.is_portal_admin:
        return {TaskStatus.TODO.value: 0, TaskStatus.IN_PROGRESS.value: 0}
    subq = apply_kpi_active_filter(
        _apply_list_tasks_filters(select(PortalTask.status), user, mine_only=False),
        kpi_excluded,
    ).subquery()
    stmt = select(subq.c.status, sa_func.count()).select_from(subq).group_by(subq.c.status)
    rows = (await session.execute(stmt)).all()
    out: dict[str, int] = {TaskStatus.TODO.value: 0, TaskStatus.IN_PROGRESS.value: 0}
    for status, cnt in rows:
        k = str(status)
        if k in out:
            out[k] = int(cnt)
    return out


async def list_admin_team_assignee_load(
    session: AsyncSession,
    user: UserPublic,
    *,
    kpi_excluded: frozenset[str],
    closed_statuses: frozenset[str] | None = None,
    limit: int = HOME_ASSIGNEE_LOAD_LIMIT,
) -> list[dict[str, Any]]:
    """Топ-N исполнителей по числу KPI-активных задач команды."""
    if not user.is_portal_admin:
        return []
    cutoff = overdue_cutoff_utc(_now_utc())
    base = _apply_list_tasks_filters(
        select(
            sa_func.coalesce(PortalTaskAssignee.assignee_sub, PortalTask.assignee_sub).label("assignee_sub"),
            PortalTask.due_at,
            PortalTask.status,
        ),
        user,
        mine_only=False,
    ).outerjoin(PortalTaskAssignee, PortalTaskAssignee.task_id == PortalTask.id)
    base = apply_kpi_active_filter(base, kpi_excluded)
    base = base.where(
        sa_func.coalesce(PortalTaskAssignee.assignee_sub, PortalTask.assignee_sub).is_not(None),
    )
    subq = base.subquery()
    from app.portal_collab.services._task_home_common import _resolve_closed_statuses

    closed = _resolve_closed_statuses(closed_statuses)
    is_overdue = subq.c.due_at.is_not(None) & (subq.c.due_at < cutoff) & subq.c.status.not_in(closed)
    stmt = (
        select(
            subq.c.assignee_sub,
            sa_func.count().label("open_count"),
            sa_func.sum(case((is_overdue, 1), else_=0)).label("overdue_count"),
            sa_func.coalesce(
                PortalUserProfile.full_name,
                PortalUserProfile.email,
                PortalUserProfile.username,
                subq.c.assignee_sub,
            ).label("display_name"),
            PortalUserProfile.email,
        )
        .select_from(subq)
        .outerjoin(PortalUserProfile, PortalUserProfile.sub == subq.c.assignee_sub)
        .group_by(
            subq.c.assignee_sub,
            PortalUserProfile.full_name,
            PortalUserProfile.email,
            PortalUserProfile.username,
        )
        .order_by(sa_func.count().desc())
        .limit(limit)
    )
    rows = (await session.execute(stmt)).all()
    return [
        {
            "assignee_sub": str(row.assignee_sub),
            "open_count": int(row.open_count),
            "overdue_count": int(row.overdue_count),
            "display_name": str(row.display_name) if row.display_name is not None else None,
            "avatar_url": _avatar_url_from_profile(user_sub=str(row.assignee_sub), email=row.email),
            "avatar_focal_x": None,
            "avatar_focal_y": None,
        }
        for row in rows
    ]
