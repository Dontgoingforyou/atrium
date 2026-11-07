"""Формат текста напоминаний о событии (публичные format / reminder_email)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.infrastructure.email.reminder_format import (
    format_calendar_reminder_detail_lines,
    format_reminder_when,
)
from app.infrastructure.email.templates import reminder_email


def test_format_reminder_when_always_msk() -> None:
    starts = datetime(2026, 8, 6, 10, 0, tzinfo=UTC)
    assert format_reminder_when(starts, timezone="Europe/Moscow") == "06.08.2026 13:00 МСК"
    assert format_reminder_when(starts, timezone="UTC") == "06.08.2026 13:00 МСК"


def test_format_calendar_reminder_detail_lines_with_location() -> None:
    starts = datetime(2026, 8, 6, 10, 0, tzinfo=UTC)
    lines = format_calendar_reminder_detail_lines(
        event_title="Стендап",
        starts_at=starts,
        location="https://telemost.yandex.ru/j/1",
        timezone="UTC",
    )
    assert lines[0] == "Напоминание о событии: «Стендап»"
    assert lines[1] == "Когда: 06.08.2026 13:00 МСК"
    assert lines[2] == "Место: https://telemost.yandex.ru/j/1"


def test_reminder_email_uses_msk_and_location() -> None:
    starts = datetime(2026, 8, 6, 10, 0, tzinfo=UTC)
    subject, text, html = reminder_email(
        event_title="Стендап",
        starts_at=starts,
        location="Офис / ссылка",
        timezone="UTC",
    )
    assert subject == "Напоминание: Стендап"
    assert "Стендап" in text
    assert "06.08.2026 13:00 МСК" in text
    assert "Офис / ссылка" in text
    assert "06.08.2026 13:00 МСК" in html
