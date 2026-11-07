"""Общие константы и хелперы домашнего экрана задач."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import case, select, true

from app.core.enums import TaskPriority, TaskStatus
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.portal_collab.services._task_due_calendar import month_start_utc, overdue_cutoff_utc
from app.services.user_photo_url import build_user_photo_proxy_url

_CLOSED_TASK_STATUSES: tuple[str, ...] = (TaskStatus.DONE.value, TaskStatus.CANCELLED.value)
# Одна пара с FE (`taskColumns.ts`); сверяет taskColumnTitlePatternsSync.test.ts.
DONE_LIKE_COLUMN_TITLE_PATTERN = r"^(готов[аоыея]*|завершен[аоыея]*|выполнен[аоыея]*|done|completed)$"
APPROVAL_LIKE_COLUMN_TITLE_PATTERN = r"^(на\s+согласовании|согласован[аоыея]*)$"
CANCELLED_LIKE_COLUMN_TITLE_PATTERN = r"^(отменен[аоыея]*|cancelled)$"
_DONE_LIKE_COLUMN_TITLE_RE = re.compile(DONE_LIKE_COLUMN_TITLE_PATTERN, re.IGNORECASE | re.UNICODE)
_APPROVAL_LIKE_COLUMN_TITLE_RE = re.compile(APPROVAL_LIKE_COLUMN_TITLE_PATTERN, re.IGNORECASE | re.UNICODE)
_CANCELLED_LIKE_COLUMN_TITLE_RE = re.compile(CANCELLED_LIKE_COLUMN_TITLE_PATTERN, re.IGNORECASE | re.UNICODE)
_PRIORITY_ORDER: tuple[str, ...] = (TaskPriority.LOW.value, TaskPriority.MEDIUM.value, TaskPriority.HIGH.value)
HOME_ASSIGNEE_LOAD_LIMIT = 20


def is_done_like_column_title(title: str) -> bool:
    """Колонка «Готово» / завершена — чип «Завершена», не «На согласовании»."""
    return bool(_DONE_LIKE_COLUMN_TITLE_RE.match(title.strip()))


def is_approval_like_column_title(title: str) -> bool:
    """Колонка согласования: закрытая для KPI, но не «Завершена»."""
    return bool(_APPROVAL_LIKE_COLUMN_TITLE_RE.match(title.strip()))


def is_cancelled_like_column_title(title: str) -> bool:
    """Колонка отмены (title), не путать с done-like."""
    return bool(_CANCELLED_LIKE_COLUMN_TITLE_RE.match(title.strip()))


def _avatar_url_from_profile(*, user_sub: str, email: str | None) -> str | None:
    return build_user_photo_proxy_url(user_sub=user_sub, email=email)


def _empty_open_priority_counts() -> dict[str, int]:
    return {k: 0 for k in _PRIORITY_ORDER}


def _resolve_closed_statuses(closed_statuses: frozenset[str] | None) -> frozenset[str]:
    if closed_statuses is not None:
        return closed_statuses
    return frozenset(_CLOSED_TASK_STATUSES)


def _kpi_active_expr(kpi_excluded: frozenset[str]) -> Any:
    if kpi_excluded:
        return PortalTask.status.not_in(kpi_excluded)
    return true()


def _is_overdue_expr(
    now: datetime,
    kpi_excluded: frozenset[str],
    closed_statuses: frozenset[str] | None = None,
) -> Any:
    """KPI-активная задача с прошедшим календарным днём срока; закрытые не просрочены."""
    closed = _resolve_closed_statuses(closed_statuses)
    cutoff = overdue_cutoff_utc(now)
    return (
        _kpi_active_expr(kpi_excluded)
        & PortalTask.status.not_in(closed)
        & PortalTask.due_at.is_not(None)
        & (PortalTask.due_at < cutoff)
    )


def _home_kpi_task_order_by(
    now: datetime,
    kpi_excluded: frozenset[str],
    closed_statuses: frozenset[str] | None = None,
) -> Any:
    """Сортировка KPI-активных задач: просроченные → по сроку → по дате создания."""
    is_overdue = _is_overdue_expr(now, kpi_excluded, closed_statuses)
    return (
        case((is_overdue, 0), else_=1).asc(),
        PortalTask.due_at.is_(None),
        PortalTask.due_at.asc(),
        PortalTask.created_at.desc(),
    )


def _home_my_tasks_order_by(
    now: datetime,
    kpi_excluded: frozenset[str],
    closed_statuses: frozenset[str] | None = None,
) -> Any:
    """Сортировка «Мои задачи»: KPI-активные выше, затем просроченные, закрытые по updated_at."""
    kpi_active = _kpi_active_expr(kpi_excluded)
    is_overdue = _is_overdue_expr(now, kpi_excluded, closed_statuses)
    return (
        case((kpi_active, 0), else_=1).asc(),
        case((is_overdue, 0), else_=1).asc(),
        PortalTask.due_at.is_(None),
        PortalTask.due_at.asc(),
        PortalTask.updated_at.desc(),
        PortalTask.created_at.desc(),
    )


def apply_done_this_month_filter(
    stmt: Any,
    closed_statuses: frozenset[str] | None = None,
    *,
    month_start: datetime | None = None,
) -> Any:
    """Закрытые (done-like ∪ approval-like ∪ cancelled) с начала месяца портала — KPI и list_tasks."""
    closed = _resolve_closed_statuses(closed_statuses)
    start = month_start if month_start is not None else month_start_utc(_now_utc())
    return stmt.where(
        PortalTask.status.in_(tuple(closed)),
        PortalTask.updated_at >= start,
    )


def apply_no_assignee_filter(stmt: Any) -> Any:
    """Нет колоночного исполнителя и нет строк в junction — KPI и list_tasks."""
    return stmt.where(
        PortalTask.assignee_sub.is_(None),
        ~PortalTask.id.in_(select(PortalTaskAssignee.task_id)),
    )
