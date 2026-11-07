from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.portal_collab.services import task_home as task_home_svc
from app.portal_collab.services.task import tasks_to_reads
from app.portal_collab.services.task_column import task_column_status_sets
from app.portal_favorites.services import favorite as favorite_svc
from app.portal_home.schemas.home import (
    AdminHomeBlock,
    AssigneeHomeDrilldown,
    ManagerHomeBlock,
    PortalHomeRead,
    PortalHomeSearchHint,
    TaskByStatusRead,
    TaskOpenByPriorityRead,
    TeamAssigneeLoad,
)
from app.schemas.auth import UserPublic

HOME_TASKS_PREVIEW_LIMIT = 8
HOME_FAVORITES_PREVIEW_LIMIT = 8
HOME_ADMIN_TEAM_TASKS_PREVIEW_LIMIT = 8
HOME_ASSIGNEE_PREVIEW_LIMIT = 8


async def _build_admin_block(
    session: AsyncSession,
    user: UserPublic,
    *,
    kpi_excluded: frozenset[str],
    closed_statuses: frozenset[str],
) -> AdminHomeBlock | None:
    """Дашборд администратора портала: задачи команды. `None` для не-администратора."""
    if not user.is_portal_admin:
        return None
    team_open, team_overdue = await task_home_svc.count_admin_team_tasks_home_summary(
        session, user, kpi_excluded=kpi_excluded, closed_statuses=closed_statuses
    )
    team_preview_rows = await task_home_svc.list_admin_team_tasks_home_preview(
        session,
        user,
        limit=HOME_ADMIN_TEAM_TASKS_PREVIEW_LIMIT,
        kpi_excluded=kpi_excluded,
        closed_statuses=closed_statuses,
    )
    team_by_pr = await task_home_svc.count_admin_team_open_tasks_by_priority(session, user, kpi_excluded=kpi_excluded)
    team_done = await task_home_svc.count_admin_team_done_this_month(session, user)
    team_no_assignee = await task_home_svc.count_admin_team_no_assignee(session, user, kpi_excluded=kpi_excluded)
    team_by_status = await task_home_svc.count_admin_team_tasks_by_status(session, user, kpi_excluded=kpi_excluded)
    assignee_load_rows = await task_home_svc.list_admin_team_assignee_load(
        session, user, kpi_excluded=kpi_excluded, closed_statuses=closed_statuses
    )
    return AdminHomeBlock(
        team_open_count=team_open,
        team_overdue_count=team_overdue,
        team_tasks_preview=await tasks_to_reads(session, team_preview_rows),
        team_open_by_priority=TaskOpenByPriorityRead.model_validate(team_by_pr),
        team_done_this_month=team_done,
        team_no_assignee_count=team_no_assignee,
        team_by_status=TaskByStatusRead.model_validate(team_by_status),
        team_assignee_load=[TeamAssigneeLoad.model_validate(r) for r in assignee_load_rows],
    )


async def _build_assignee_drilldown(
    session: AsyncSession,
    user: UserPublic,
    assignee_sub: str,
    *,
    kpi_excluded: frozenset[str],
    closed_statuses: frozenset[str],
) -> AssigneeHomeDrilldown:
    """Drill-down по одному исполнителю: доступен менеджеру или администратору (RBAC — в task_home_svc)."""
    open_c, overdue_c = await task_home_svc.count_assignee_open_tasks_home(
        session, user, assignee_sub, kpi_excluded=kpi_excluded, closed_statuses=closed_statuses
    )
    open_rows = await task_home_svc.list_assignee_open_tasks_home_preview(
        session,
        user,
        assignee_sub,
        limit=HOME_ASSIGNEE_PREVIEW_LIMIT,
        kpi_excluded=kpi_excluded,
        overdue_only=False,
        closed_statuses=closed_statuses,
    )
    overdue_rows = await task_home_svc.list_assignee_open_tasks_home_preview(
        session,
        user,
        assignee_sub,
        limit=HOME_ASSIGNEE_PREVIEW_LIMIT,
        kpi_excluded=kpi_excluded,
        overdue_only=True,
        closed_statuses=closed_statuses,
    )
    display_name, avatar_url, avatar_focal_x, avatar_focal_y = await task_home_svc.get_assignee_display_info(
        session, assignee_sub
    )
    by_pr = await task_home_svc.count_assignee_open_tasks_by_priority(
        session, user, assignee_sub, kpi_excluded=kpi_excluded
    )
    return AssigneeHomeDrilldown(
        assignee_sub=assignee_sub,
        display_name=display_name,
        avatar_url=avatar_url,
        avatar_focal_x=avatar_focal_x,
        avatar_focal_y=avatar_focal_y,
        open_count=open_c,
        overdue_count=overdue_c,
        open_tasks_preview=await tasks_to_reads(session, open_rows),
        overdue_tasks_preview=await tasks_to_reads(session, overdue_rows),
        open_by_priority=TaskOpenByPriorityRead.model_validate(by_pr),
    )


async def build_portal_home(
    session: AsyncSession,
    user: UserPublic,
    *,
    assignee_sub: str | None = None,
) -> PortalHomeRead:
    """Собирает ответ главной: превью задач, избранное, опционально дашборд админа.

    Поле ``manager`` зарезервировано и всегда ``None`` (реализация не завершена).
    Запросы к БД — последовательно: одна AsyncSession не допускает concurrent operations.
    """
    column_sets = await task_column_status_sets(session)
    kpi_excluded = column_sets.kpi_inactive
    closed_statuses = column_sets.closed

    my_rows = await task_home_svc.list_my_tasks_home_preview(
        session,
        user,
        limit=HOME_TASKS_PREVIEW_LIMIT,
        kpi_excluded=kpi_excluded,
        closed_statuses=closed_statuses,
    )
    my_open, my_overdue = await task_home_svc.count_my_tasks_home_summary(
        session, user, kpi_excluded=kpi_excluded, closed_statuses=closed_statuses
    )
    favorites_preview = await favorite_svc.list_favorites(session, user, limit=HOME_FAVORITES_PREVIEW_LIMIT)

    admin = await _build_admin_block(session, user, kpi_excluded=kpi_excluded, closed_statuses=closed_statuses)

    manager: ManagerHomeBlock | None = None

    assignee_drilldown: AssigneeHomeDrilldown | None = None
    if assignee_sub:
        assignee_drilldown = await _build_assignee_drilldown(
            session, user, assignee_sub, kpi_excluded=kpi_excluded, closed_statuses=closed_statuses
        )

    return PortalHomeRead(
        my_tasks_preview=await tasks_to_reads(session, my_rows),
        my_tasks_open_count=my_open,
        my_tasks_overdue_count=my_overdue,
        favorites_preview=favorites_preview,
        search=PortalHomeSearchHint(),
        admin=admin,
        manager=manager,
        assignee_drilldown=assignee_drilldown,
    )
