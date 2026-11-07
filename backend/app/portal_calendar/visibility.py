"""Какие календари микросервиса попадают на экран портала."""

from __future__ import annotations

from collections.abc import Iterable

from app.portal_calendar.schemas.calendar import CalendarRead


def owned_calendars(calendars: Iterable[CalendarRead], owner_sub: str) -> list[CalendarRead]:
    """Только календари вызывающего. Чужое членство и весь отдел сюда не входят."""
    return [item for item in calendars if item.owner_sub == owner_sub]


def shown_to_other_departments(calendars: Iterable[CalendarRead]) -> list[CalendarRead]:
    return [item for item in calendars if item.show_to_other_departments]
