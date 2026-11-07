"""XSS-экранирование HTML-писем календаря."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from app.infrastructure.email.templates import (
    calendar_share_email,
    event_invite_email,
    reminder_email,
)

_XSS_NAME = "<script>alert(1)</script>"
_XSS_TITLE = 'Встреча "<img src=x onerror=alert(1)>"'
_XSS_LOCATION = "<img src=x onerror=alert(1)>"
_XSS_URL = 'https://evil.example/" onclick="alert(1)'
_XSS_ROLE = 'editor"><script>x</script>'
_STARTS = datetime(2026, 1, 15, 10, 0, tzinfo=UTC)


def test_event_invite_email_escapes_html_and_href() -> None:
    _subject, text, html = event_invite_email(
        event_title=_XSS_TITLE,
        starts_at=_STARTS,
        location=_XSS_LOCATION,
        invite_url=_XSS_URL,
        organizer_name=_XSS_NAME,
    )
    assert "<script>" not in html
    assert "<img" not in html
    assert escape(_XSS_NAME) in html
    assert escape(_XSS_TITLE) in html
    assert escape(_XSS_LOCATION) in html
    assert f'href="{escape(_XSS_URL, quote=True)}"' in html
    assert 'href="https://evil.example/"' not in html
    assert _XSS_TITLE in text
    assert _XSS_URL in text


def test_calendar_share_email_escapes_html_and_href() -> None:
    _subject, text, html = calendar_share_email(
        calendar_title=_XSS_TITLE,
        role=_XSS_ROLE,
        invite_url=_XSS_URL,
        organizer_name=_XSS_NAME,
    )
    assert "<script>" not in html
    assert escape(_XSS_NAME) in html
    assert escape(_XSS_TITLE) in html
    assert escape(_XSS_ROLE) in html
    assert f'href="{escape(_XSS_URL, quote=True)}"' in html
    assert 'href="https://evil.example/"' not in html
    assert _XSS_URL in text


def test_reminder_email_escapes_title_and_location() -> None:
    _subject, text, html = reminder_email(
        event_title=_XSS_TITLE,
        starts_at=_STARTS,
        location=_XSS_LOCATION,
    )
    assert "<script>" not in html
    assert "<img" not in html
    assert escape(_XSS_TITLE) in html
    assert escape(_XSS_LOCATION) in html
    assert _XSS_TITLE in text
    assert _XSS_LOCATION in text
