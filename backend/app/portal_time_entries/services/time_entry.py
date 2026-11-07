from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.core.optimistic_lock import compare_and_swap_row
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_time_entry import PortalTimeEntry
from app.portal_collab.services import task as task_svc
from app.portal_time_entries.schemas.time_entry import (
    PortalTimeEntryBulkCreate,
    PortalTimeEntryCreate,
    PortalTimeEntrySummaryRead,
    PortalTimeEntryUpdate,
)
from app.portal_time_entries.services._jira_csv_import import (
    import_jira_worklog_csv,
)
from app.portal_time_entries.services._time_entry_reports import (
    ensure_timesheets_access as _ensure_timesheets_access,
)
from app.portal_time_entries.services._time_entry_reports import (
    get_time_entries_report,
    list_specialists_monthly_summary,
    month_date_range,
    user_is_developer,
)
from app.portal_time_entries.services._time_entry_reports import (
    list_where_criteria as _list_where_criteria,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

__all__ = [
    "get_time_entries_report",
    "import_jira_worklog_csv",
    "list_specialists_monthly_summary",
    "month_date_range",
    "user_is_developer",
]


def _ensure_can_access_entry(user: UserPublic, entry: PortalTimeEntry) -> None:
    if user.is_portal_admin:
        return
    if entry.user_sub != user.sub:
        logger.warning(
            "Отказ в доступе: user_sub=%s resource=time_entry/%s",
            user.sub,
            entry.id,
        )
        raise ForbiddenError("Нет доступа к записи таймшита")


# ---------------------------------------------------------------------------
# Вспомогательные функции фильтрации
# ---------------------------------------------------------------------------

_MAX_BULK_ENTRIES = 200


def _generate_dates(date_from: date, date_to: date, weekdays: list[int], *, max_dates: int) -> list[date]:
    """Даты в диапазоне [date_from, date_to], у которых date.weekday() входит в weekdays.

    Останавливается после ``max_dates + 1`` совпадений — чтобы не обходить годы 1…9999
    до проверки лимита bulk.
    """
    allowed = set(weekdays)
    dates: list[date] = []
    current = date_from
    while current <= date_to:
        if current.weekday() in allowed:
            dates.append(current)
            if len(dates) > max_dates:
                return dates
        current += timedelta(days=1)
    return dates


async def _validate_task_link(session: AsyncSession, user: UserPublic, task_id: uuid.UUID | None) -> None:
    if task_id is None:
        return
    task = await session.get(PortalTask, task_id)
    if task is None:
        raise NotFoundError("Задача не найдена")
    if not await task_svc.user_can_view_task(session, user, task):
        raise ForbiddenError("Нет доступа к задаче")


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


async def create_time_entry(
    session: AsyncSession,
    user: UserPublic,
    data: PortalTimeEntryCreate,
) -> PortalTimeEntry:
    _ensure_timesheets_access(user, log_denial=True)
    await _validate_task_link(session, user, data.task_id)
    row = PortalTimeEntry(
        user_sub=user.sub,
        task_id=data.task_id,
        task_name=data.task_name,
        worked_on=data.worked_on,
        minutes=data.minutes,
        note=data.note,
        is_tour_demo=bool(data.is_tour_demo),
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


async def create_time_entries_bulk(
    session: AsyncSession,
    user: UserPublic,
    data: PortalTimeEntryBulkCreate,
) -> list[PortalTimeEntry]:
    """
    Массовое создание повторяющихся записей по диапазону дат и дням недели.
    """
    _ensure_timesheets_access(user, log_denial=True)
    await _validate_task_link(session, user, data.task_id)

    if data.date_to < data.date_from:
        raise ValidationError("Дата «по» не может быть раньше даты «с»")
    if not data.weekdays:
        raise ValidationError("Укажите хотя бы один день недели")

    dates = _generate_dates(data.date_from, data.date_to, data.weekdays, max_dates=_MAX_BULK_ENTRIES)
    if not dates:
        raise ValidationError("В выбранном диапазоне нет дат с указанными днями недели")
    if len(dates) > _MAX_BULK_ENTRIES:
        raise ValidationError(f"Слишком много записей за раз (максимум {_MAX_BULK_ENTRIES}, получилось {len(dates)})")

    timestamp = _now_utc()
    rows = [
        PortalTimeEntry(
            user_sub=user.sub,
            task_id=data.task_id,
            task_name=data.task_name,
            worked_on=worked_on,
            minutes=data.minutes,
            note=data.note,
            created_at=timestamp,
            updated_at=timestamp,
        )
        for worked_on in dates
    ]
    session.add_all(rows)
    await session.commit()
    return rows


async def list_time_entries(
    session: AsyncSession,
    user: UserPublic,
    *,
    filter_user_sub: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    task_id: uuid.UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[PortalTimeEntry], int]:
    _ensure_timesheets_access(user)
    criteria = _list_where_criteria(
        user=user,
        filter_user_sub=filter_user_sub,
        date_from=date_from,
        date_to=date_to,
        task_id=task_id,
    )
    base_stmt = select(PortalTimeEntry).order_by(PortalTimeEntry.worked_on.desc(), PortalTimeEntry.created_at.desc())
    for c in criteria:
        base_stmt = base_stmt.where(c)

    count_stmt = select(sa_func.count()).select_from(base_stmt.subquery())
    total: int = (await session.execute(count_stmt)).scalar_one()

    rows = list((await session.scalars(base_stmt.limit(limit).offset(offset))).all())
    return rows, total


async def summarize_time_entries(
    session: AsyncSession,
    user: UserPublic,
    *,
    filter_user_sub: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    task_id: uuid.UUID | None = None,
) -> PortalTimeEntrySummaryRead:
    # Исключение из правила «сервис возвращает ORM»: агрегат без соответствующей ORM-модели.
    _ensure_timesheets_access(user)
    criteria = _list_where_criteria(
        user=user,
        filter_user_sub=filter_user_sub,
        date_from=date_from,
        date_to=date_to,
        task_id=task_id,
    )
    stmt = select(
        sa_func.coalesce(sa_func.sum(PortalTimeEntry.minutes), 0),
        sa_func.count(PortalTimeEntry.id),
    ).select_from(PortalTimeEntry)
    for c in criteria:
        stmt = stmt.where(c)
    total, count = (await session.execute(stmt)).one()
    return PortalTimeEntrySummaryRead(total_minutes=int(total), entries_count=int(count))


async def update_time_entry(
    session: AsyncSession,
    user: UserPublic,
    entry_id: uuid.UUID,
    data: PortalTimeEntryUpdate,
) -> PortalTimeEntry:
    _ensure_timesheets_access(user, log_denial=True)
    row = await session.get(PortalTimeEntry, entry_id)
    if row is None:
        raise NotFoundError("Запись не найдена")
    _ensure_can_access_entry(user, row)
    patch = data.model_dump(exclude_unset=True)
    patch.pop("expected_version", None)
    next_task_id = patch["task_id"] if "task_id" in patch else row.task_id
    await _validate_task_link(session, user, next_task_id)

    if not patch:
        return row

    values: dict[str, Any] = {"updated_at": _now_utc()}
    for field in ("worked_on", "minutes", "task_id", "task_name", "note"):
        if field in patch:
            values[field] = patch[field]

    new_version = await compare_and_swap_row(
        session,
        PortalTimeEntry,
        entity_id=entry_id,
        expected_version=data.expected_version,
        values=values,
        conflict_message="Запись времени изменена другим пользователем",
    )
    await session.refresh(row)
    row.version = new_version
    await session.commit()
    await session.refresh(row)
    return row


async def delete_time_entry(session: AsyncSession, user: UserPublic, entry_id: uuid.UUID) -> None:
    _ensure_timesheets_access(user, log_denial=True)
    row = await session.get(PortalTimeEntry, entry_id)
    if row is None:
        raise NotFoundError("Запись не найдена")
    _ensure_can_access_entry(user, row)
    await session.delete(row)
    await session.commit()
