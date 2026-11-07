"""Календарный cutoff просрочки: день дедлайна ещё не просрочен."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.portal_collab.services._notification_access import TASK_REMINDER_KIND_OVERDUE
from app.portal_collab.services._task_due_calendar import month_start_utc, overdue_cutoff_utc, today_portal
from app.portal_collab.services._task_due_reminders import reminder_kind_for_due

_MSK = ZoneInfo("Europe/Moscow")


def test_overdue_cutoff_is_start_of_moscow_day() -> None:
    now = datetime(2026, 9, 15, 12, 0, tzinfo=_MSK)
    assert overdue_cutoff_utc(now) == datetime(2026, 9, 14, 21, 0, tzinfo=UTC)
    assert today_portal(now) == datetime(2026, 9, 15).date()


def test_month_start_is_start_of_moscow_month() -> None:
    now = datetime(2026, 9, 15, 12, 0, tzinfo=_MSK)
    assert month_start_utc(now) == datetime(2026, 8, 31, 21, 0, tzinfo=UTC)
    late_aug_utc = datetime(2026, 8, 31, 22, 0, tzinfo=UTC)
    assert month_start_utc(late_aug_utc) == datetime(2026, 8, 31, 21, 0, tzinfo=UTC)


def test_due_today_is_not_overdue_kind() -> None:
    now = datetime(2026, 9, 15, 18, 17, tzinfo=_MSK)
    due_today = datetime(2026, 9, 15, tzinfo=UTC)
    due_yesterday = datetime(2026, 9, 14, tzinfo=UTC)
    assert reminder_kind_for_due(due_today, now) is None
    assert reminder_kind_for_due(due_yesterday, now) == TASK_REMINDER_KIND_OVERDUE
    assert due_today >= overdue_cutoff_utc(now)
    assert due_yesterday < overdue_cutoff_utc(now)
