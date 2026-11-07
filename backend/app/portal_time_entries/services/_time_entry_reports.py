"""Отчёты и агрегации по записям времени.

Содержит публичные функции отчётов, а также зависимые хелперы периодов и фильтрации.
"""

from __future__ import annotations

import calendar
import logging
import uuid
from collections import defaultdict
from datetime import date, timedelta
from typing import Any, Literal

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_constants import IDP_GROUP_DEVELOPER
from app.core.exceptions import ForbiddenError, ValidationError
from app.core.permissions import is_manager_or_admin, is_timesheet_only, require_manager_or_admin
from app.infrastructure.db.models.portal_time_entry import PortalTimeEntry
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_time_entries.schemas.time_entry import (
    PortalSpecialistMonthlySummary,
    PortalTimeEntryReportBucket,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Хелперы ролей и доступа (общие для time_entry.py и отчётов)
# ---------------------------------------------------------------------------


def user_is_developer(user: UserPublic) -> bool:
    """Пользователь имеет роль разработчика (Keycloak-группа «students»)."""
    return IDP_GROUP_DEVELOPER in user.idp_groups


def ensure_timesheets_access(user: UserPublic, *, log_denial: bool = False) -> None:
    """Доступ к разделу таймшитов: admin, менеджер, students или должность «только ТШ».

    ``log_denial=True`` — для мутаций (аудит IDOR/RBAC). Списки и сводки не логируем,
    чтобы не шуметь на каждом отказе чтения.
    """
    if user.is_portal_admin or is_manager_or_admin(user) or is_timesheet_only(user):
        return
    if log_denial:
        logger.warning("Отказ в доступе: user_sub=%s resource=timesheets", user.sub)
    raise ForbiddenError("Нет доступа к разделу таймшитов")


# ---------------------------------------------------------------------------
# Утилиты фильтрации (переиспользуются в time_entry.py)
# ---------------------------------------------------------------------------


def effective_user_sub_filter(user: UserPublic, requested_user_sub: str | None) -> str | None:
    """Для обычного пользователя — только свой sub; админ — по ``user_sub``; менеджер
    АУ (``gid_number`` отдела Аутстафф, не группа Keycloak ``outstaff``) — чужие записи
    при явном ``user_sub``.
    """
    if user.is_portal_admin:
        return requested_user_sub
    if is_manager_or_admin(user):
        if requested_user_sub is not None:
            return requested_user_sub
        return user.sub
    if requested_user_sub is not None and requested_user_sub != user.sub:
        raise ForbiddenError("Нельзя запрашивать чужие записи")
    return user.sub


def list_where_criteria(
    *,
    user: UserPublic,
    filter_user_sub: str | None,
    date_from: date | None,
    date_to: date | None,
    task_id: uuid.UUID | None,
) -> list[Any]:
    eff_sub = effective_user_sub_filter(user, filter_user_sub)
    criteria: list[Any] = []
    if eff_sub is not None:
        criteria.append(PortalTimeEntry.user_sub == eff_sub)
    if date_from is not None:
        criteria.append(PortalTimeEntry.worked_on >= date_from)
    if date_to is not None:
        criteria.append(PortalTimeEntry.worked_on <= date_to)
    if task_id is not None:
        criteria.append(PortalTimeEntry.task_id == task_id)
    return criteria


def month_date_range(month: str) -> tuple[date, date]:
    """Конвертирует строку «YYYY-MM» в диапазон дат (первый—последний день месяца)."""
    if len(month) != 7 or month[4] != "-":
        raise ValidationError("Месяц должен быть в формате YYYY-MM")
    try:
        year = int(month[:4])
        mon = int(month[5:7])
        first_day = date(year, mon, 1)
    except ValueError as exc:
        raise ValidationError("Месяц должен быть в формате YYYY-MM") from exc
    last_day = date(year, mon, calendar.monthrange(year, mon)[1])
    return first_day, last_day


# ---------------------------------------------------------------------------
# Приватные утилиты периодов
# ---------------------------------------------------------------------------


def _week_key(d: date) -> tuple[int, int]:
    iso = d.isocalendar()
    return iso.year, iso.week


def _week_bounds(year: int, week: int) -> tuple[date, date]:
    """Первый (пн) и последний (вс) день ISO-недели."""
    start = date.fromisocalendar(year, week, 1)
    end = start + timedelta(days=6)
    return start, end


def _month_key(d: date) -> tuple[int, int]:
    return d.year, d.month


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    first = date(year, month, 1)
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last


# ---------------------------------------------------------------------------
# Публичные функции отчётов
# ---------------------------------------------------------------------------


async def get_time_entries_report(
    session: AsyncSession,
    user: UserPublic,
    *,
    group_by: Literal["week", "month"] = "week",
    filter_user_sub: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    task_id: uuid.UUID | None = None,
) -> list[PortalTimeEntryReportBucket]:
    """Периодический отчёт: группировка записей по неделям или месяцам.

    Исключение из правила «сервис возвращает ORM»: агрегат без соответствующей ORM-модели.

    RBAC: те же правила, что у list_time_entries — обычный пользователь видит только свои данные.
    Выборка только (дата, минуты) без лимита строк; ISO-неделя считается в Python
    (одинаково на PostgreSQL и SQLite).
    """
    ensure_timesheets_access(user)
    criteria = list_where_criteria(
        user=user,
        filter_user_sub=filter_user_sub,
        date_from=date_from,
        date_to=date_to,
        task_id=task_id,
    )
    stmt = select(PortalTimeEntry.worked_on, PortalTimeEntry.minutes).select_from(PortalTimeEntry)
    for c in criteria:
        stmt = stmt.where(c)

    rows = list((await session.execute(stmt)).all())
    buckets: dict[tuple[int, int], dict[str, int]] = defaultdict(lambda: {"total_minutes": 0, "entries_count": 0})
    key_fn = _week_key if group_by == "week" else _month_key
    bounds_fn = _week_bounds if group_by == "week" else _month_bounds
    for worked_on, minutes in rows:
        key = key_fn(worked_on)
        buckets[key]["total_minutes"] += minutes
        buckets[key]["entries_count"] += 1

    result: list[PortalTimeEntryReportBucket] = []
    for (year, second), data in sorted(buckets.items()):
        start, end = bounds_fn(year, second)
        label = f"{year}-W{second:02d}" if group_by == "week" else f"{year}-{second:02d}"
        result.append(
            PortalTimeEntryReportBucket(
                period_label=label,
                date_start=start,
                date_end=end,
                total_minutes=data["total_minutes"],
                entries_count=data["entries_count"],
            )
        )
    return result


async def list_specialists_monthly_summary(
    session: AsyncSession,
    user: UserPublic,
    *,
    month: str,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[PortalSpecialistMonthlySummary], int]:
    """Список специалистов с суммарными часами за выбранный месяц.

    Исключение из правила «сервис возвращает ORM»: агрегат GROUP BY без соответствующей ORM-модели.

    Доступен только менеджеру или администратору портала.
    Возвращает всех пользователей, у которых есть записи за период.
    Агрегация выполняется в БД одним запросом (GROUP BY + JOIN с профилем).
    """
    require_manager_or_admin(
        user,
        "Доступ к списку специалистов — только для менеджера или администратора",
    )

    date_from, date_to = month_date_range(month)

    base_stmt = (
        select(
            PortalTimeEntry.user_sub,
            PortalUserProfile.full_name,
            PortalUserProfile.email,
            sa_func.sum(PortalTimeEntry.minutes).label("total_minutes"),
            sa_func.count(PortalTimeEntry.id).label("entries_count"),
        )
        .join(PortalUserProfile, PortalTimeEntry.user_sub == PortalUserProfile.sub, isouter=True)
        .where(PortalTimeEntry.worked_on >= date_from)
        .where(PortalTimeEntry.worked_on <= date_to)
        .group_by(PortalTimeEntry.user_sub, PortalUserProfile.full_name, PortalUserProfile.email)
        .order_by(PortalTimeEntry.user_sub)
    )

    count_stmt = select(sa_func.count()).select_from(base_stmt.subquery())
    total: int = (await session.execute(count_stmt)).scalar_one()

    data_stmt = base_stmt.limit(limit).offset(offset)
    rows = list((await session.execute(data_stmt)).all())

    items = [
        PortalSpecialistMonthlySummary(
            user_sub=row.user_sub,
            full_name=row.full_name,
            email=row.email,
            total_minutes=int(row.total_minutes),
            entries_count=int(row.entries_count),
            month=month,
        )
        for row in rows
    ]
    return items, total
