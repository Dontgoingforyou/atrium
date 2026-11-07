"""Извлечение http(s)-ссылки на встречу из полей события."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.portal_telegram.services.calendar_meeting_url import (
    calendar_meeting_http_url,
    calendar_meeting_url_for_notification,
    first_http_url,
)


def test_first_http_url_returns_first_https() -> None:
    assert first_http_url("см. https://telemost.yandex.ru/j/1 и ещё") == "https://telemost.yandex.ru/j/1"


def test_first_http_url_strips_trailing_punctuation() -> None:
    assert first_http_url("ссылка https://meet.google.com/abc-defg-hij.") == "https://meet.google.com/abc-defg-hij"


def test_first_http_url_skips_empty_then_reads_next() -> None:
    assert first_http_url(None, "", "  ", "http://example.com/j") == "http://example.com/j"


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        "в телемосте",
        "javascript:alert(1)",
        "data:text/html,alert(1)",
        "ftp://files.example/meet",
    ],
)
def test_first_http_url_rejects_non_http_and_empty(text: str | None) -> None:
    assert first_http_url(text) is None


def test_calendar_meeting_http_url_location_wins_over_description() -> None:
    got = calendar_meeting_http_url(
        location="Zoom https://zoom.us/j/111",
        description="запасной https://telemost.yandex.ru/j/222",
    )
    assert got == "https://zoom.us/j/111"


def test_calendar_meeting_http_url_falls_back_to_description() -> None:
    got = calendar_meeting_http_url(
        location="Переговорка",
        description="подключайтесь https://telemost.yandex.ru/j/9",
    )
    assert got == "https://telemost.yandex.ru/j/9"


def test_calendar_meeting_http_url_none_when_no_link() -> None:
    assert calendar_meeting_http_url(location="в телемосте", description="без ссылки") is None


def test_calendar_meeting_url_for_notification_only_join_types() -> None:
    event = SimpleNamespace(
        location=None,
        description="https://telemost.yandex.ru/j/3",
    )
    invite = SimpleNamespace(type="calendar_invite", calendar_event=event)
    assert calendar_meeting_url_for_notification(invite) == "https://telemost.yandex.ru/j/3"

    share = SimpleNamespace(type="calendar_share", calendar_event=event)
    assert calendar_meeting_url_for_notification(share) is None
