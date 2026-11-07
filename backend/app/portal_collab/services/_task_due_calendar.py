"""Календарный день срока задачи в TZ портала (Europe/Moscow).

Срок в UI — дата без времени; в БД хранится aware UTC (обычно полночь выбранного дня).
Просрочка и окна напоминаний считают календарный день, не момент ``due_at < now``.
Перевод в Москву — только здесь; наружу cutoff и сравнения остаются в UTC.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

PORTAL_TZ = ZoneInfo("Europe/Moscow")


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def today_portal(now: datetime) -> date:
    """Сегодняшний календарный день портала."""
    return _aware_utc(now).astimezone(PORTAL_TZ).date()


def task_due_calendar_date(due_at: datetime) -> date:
    """Календарная дата срока: UTC-дата ``due_at`` (как префикс ISO на фронте)."""
    return _aware_utc(due_at).date()


def overdue_cutoff_utc(now: datetime) -> datetime:
    """Начало сегодняшнего дня портала как aware UTC.

    Просрочка: ``due_at < cutoff``. В календарный день дедлайна задача ещё не просрочена.
    """
    start_local = datetime.combine(today_portal(now), time.min, tzinfo=PORTAL_TZ)
    return start_local.astimezone(UTC)


def month_start_utc(now: datetime) -> datetime:
    """Начало календарного месяца портала (Europe/Moscow) как aware UTC.

    «Закрыто в этом месяце» сравнивает ``updated_at`` с этим cutoff, не с 1-м числом UTC.
    """
    local = _aware_utc(now).astimezone(PORTAL_TZ)
    start_local = datetime(local.year, local.month, 1, tzinfo=PORTAL_TZ)
    return start_local.astimezone(UTC)
