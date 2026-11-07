"""Единый формат даты/текста уведомлений о событии."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

# Портал ориентирован на пользователей в РФ — в текстах уведомлений всегда МСК.
_DISPLAY_TZ = ZoneInfo("Europe/Moscow")
_DISPLAY_LABEL = "МСК"


def format_reminder_when(starts_at: datetime, *, timezone: str = "UTC") -> str:
    """Дата и время события для текста уведомления (всегда МСК).

    ``timezone`` оставлен для совместимости вызовов; на отображение не влияет.
    """
    _ = timezone
    aware = starts_at if starts_at.tzinfo is not None else starts_at.replace(tzinfo=UTC)
    local = aware.astimezone(_DISPLAY_TZ)
    return f"{local.strftime('%d.%m.%Y %H:%M')} {_DISPLAY_LABEL}"


def format_calendar_event_detail_lines(
    *,
    headline: str,
    starts_at: datetime,
    location: str | None,
    timezone: str = "UTC",
) -> list[str]:
    """Строки тела: заголовок, когда, место (если есть)."""
    when = format_reminder_when(starts_at, timezone=timezone)
    lines = [headline, f"Когда: {when}"]
    if location and location.strip():
        lines.append(f"Место: {location.strip()}")
    return lines


def format_calendar_reminder_title_line(*, event_title: str) -> str:
    return f"Напоминание о событии: «{event_title}»"


def format_calendar_reminder_detail_lines(
    *,
    event_title: str,
    starts_at: datetime,
    location: str | None,
    timezone: str = "UTC",
) -> list[str]:
    """Строки тела напоминания: заголовок, когда, место (если есть)."""
    return format_calendar_event_detail_lines(
        headline=format_calendar_reminder_title_line(event_title=event_title),
        starts_at=starts_at,
        location=location,
        timezone=timezone,
    )
