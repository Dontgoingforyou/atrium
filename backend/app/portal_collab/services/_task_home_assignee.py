"""Домашний экран: сводка по конкретному исполнителю."""

from __future__ import annotations

import logging

from sqlalchemy import func as sa_func
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ForbiddenError
from app.core.permissions import is_manager_or_admin
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.services._task_home_common import (
    _avatar_url_from_profile,
    _empty_open_priority_counts,
    _home_kpi_task_order_by,
    _is_overdue_expr,
)
from app.portal_collab.services.task import _apply_list_tasks_filters
from app.portal_collab.services.task_column import apply_kpi_active_filter
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


def _require_assignee_home_access(user: UserPublic) -> None:
    if user.is_portal_admin or is_manager_or_admin(user):
        return
    logger.warning(
        "Отказ в доступе: сводка по исполнителю user_sub=%s resource=assignee_home",
        user.sub,
    )
    raise ForbiddenError("Сводка по исполнителю — только для менеджера или администратора")


# ── Конкретный исполнитель (admin / manager) ──────────────────────────────────


async def count_assignee_open_tasks_home(
    session: AsyncSession,
    user: UserPublic,
    assignee_sub: str,
    *,
    kpi_excluded: frozenset[str],
    closed_statuses: frozenset[str] | None = None,
) -> tuple[int, int]:
    """KPI-активные и просроченные задачи одного исполнителя."""
    _require_assignee_home_access(user)
    now = _now_utc()
    assignee_tasks = select(PortalTaskAssignee.task_id).where(PortalTaskAssignee.assignee_sub == assignee_sub)
    base = apply_kpi_active_filter(
        _apply_list_tasks_filters(select(PortalTask), user, mine_only=False).where(
            or_(
                PortalTask.id.in_(assignee_tasks),
                PortalTask.assignee_sub == assignee_sub,
            ),
        ),
        kpi_excluded,
    )
    open_count = int(await session.scalar(select(sa_func.count()).select_from(base.subquery())) or 0)
    overdue_base = base.where(_is_overdue_expr(now, kpi_excluded, closed_statuses))
    overdue_count = int(await session.scalar(select(sa_func.count()).select_from(overdue_base.subquery())) or 0)
    return open_count, overdue_count


async def count_assignee_open_tasks_by_priority(
    session: AsyncSession,
    user: UserPublic,
    assignee_sub: str,
    *,
    kpi_excluded: frozenset[str],
) -> dict[str, int]:
    """KPI-активные задачи одного исполнителя по приоритету."""
    _require_assignee_home_access(user)
    assignee_tasks = select(PortalTaskAssignee.task_id).where(PortalTaskAssignee.assignee_sub == assignee_sub)
    subq = apply_kpi_active_filter(
        _apply_list_tasks_filters(
            select(PortalTask.priority),
            user,
            mine_only=False,
        ).where(
            or_(
                PortalTask.id.in_(assignee_tasks),
                PortalTask.assignee_sub == assignee_sub,
            ),
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


async def get_assignee_display_info(
    session: AsyncSession,
    assignee_sub: str,
) -> tuple[str | None, str | None, float | None, float | None]:
    """Отображаемое имя и аватар исполнителя: (display_name, avatar_url, avatar_focal_x, avatar_focal_y)."""
    profile = await session.get(PortalUserProfile, assignee_sub)
    if profile is None:
        return None, None, None, None
    display_name = profile.full_name or profile.email or profile.username or assignee_sub
    return (
        display_name,
        _avatar_url_from_profile(user_sub=assignee_sub, email=profile.email),
        None,
        None,
    )


async def list_assignee_open_tasks_home_preview(
    session: AsyncSession,
    user: UserPublic,
    assignee_sub: str,
    *,
    limit: int,
    kpi_excluded: frozenset[str],
    overdue_only: bool = False,
    closed_statuses: frozenset[str] | None = None,
) -> list[PortalTask]:
    """Превью KPI-активных (или только просроченных) задач исполнителя."""
    _require_assignee_home_access(user)
    now = _now_utc()
    assignee_tasks = select(PortalTaskAssignee.task_id).where(PortalTaskAssignee.assignee_sub == assignee_sub)
    stmt = apply_kpi_active_filter(
        _apply_list_tasks_filters(
            select(PortalTask).options(selectinload(PortalTask.tags)),
            user,
            mine_only=False,
        ).where(
            or_(
                PortalTask.id.in_(assignee_tasks),
                PortalTask.assignee_sub == assignee_sub,
            ),
        ),
        kpi_excluded,
    )
    if overdue_only:
        stmt = stmt.where(_is_overdue_expr(now, kpi_excluded, closed_statuses))
    stmt = stmt.order_by(*_home_kpi_task_order_by(now, kpi_excluded, closed_statuses)).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
