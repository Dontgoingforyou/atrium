from __future__ import annotations

from app.portal_telegram.services.telegram_url_markup import (
    JOIN_BUTTON_TEXT,
    PORTAL_BUTTON_TEXT,
    body_with_fallback_link,
    inline_url_keyboard,
    notification_url_keyboard,
)


def test_inline_url_keyboard_https() -> None:
    m = inline_url_keyboard("https://portal.example/tasks/1")
    assert m is not None
    assert m.inline_keyboard[0][0].url == "https://portal.example/tasks/1"


def test_inline_url_keyboard_http_no_button() -> None:
    """Telegram API не принимает http в url-кнопке."""
    assert inline_url_keyboard("http://localhost:9088/tasks/x") is None


def test_inline_url_keyboard_invalid_scheme_returns_none() -> None:
    assert inline_url_keyboard("ftp://x") is None
    assert inline_url_keyboard("javascript:alert(1)") is None
    assert inline_url_keyboard("data:text/html,alert(1)") is None
    assert inline_url_keyboard("") is None


def test_body_with_fallback_link_plain_url_when_no_markup() -> None:
    text, mode = body_with_fallback_link("Привет", "http://localhost/x", None, fallback_anchor_text="Открыть чат")
    assert mode is None
    assert "http://localhost/x" in text
    assert "Открыть чат:" in text
    assert "Привет" in text
    assert "<a " not in text

    plain, plain_mode = body_with_fallback_link("A", "u", inline_url_keyboard("https://a.com/b"))
    assert plain_mode is None
    assert plain == "A"


def test_inline_url_keyboard_truncates_long_url() -> None:
    long_url = "https://portal.example/" + "x" * 3000
    m = inline_url_keyboard(long_url)
    assert m is not None
    assert len(m.inline_keyboard[0][0].url) == 2048


def test_body_with_fallback_link_truncates_url() -> None:
    long_u = "http://x/" + "y" * 3000
    text, mode = body_with_fallback_link("Тело", long_u, None, fallback_anchor_text="Открыть")
    assert mode is None
    assert len(text) < len(long_u) + 50  # URL обрезан до 2048 в строке ссылки
    tail = text.split("Открыть:")[-1].strip()
    assert len(tail) == 2048


def test_inline_url_keyboard_empty_button_text_falls_back() -> None:
    m = inline_url_keyboard("https://a.com/", button_text="   ")
    assert m is not None
    assert m.inline_keyboard[0][0].text == "Открыть"


def test_notification_url_keyboard_join_then_portal() -> None:
    m = notification_url_keyboard(
        "https://portal.example.com/calendar?event=1",
        meeting_url="https://telemost.yandex.ru/j/9",
    )
    assert m is not None
    row = m.inline_keyboard[0]
    assert [b.text for b in row] == [JOIN_BUTTON_TEXT, PORTAL_BUTTON_TEXT]
    assert row[0].url == "https://telemost.yandex.ru/j/9"
    assert row[1].url == "https://portal.example.com/calendar?event=1"


def test_notification_url_keyboard_http_meeting_skips_join() -> None:
    m = notification_url_keyboard(
        "https://portal.example.com/calendar",
        meeting_url="http://intranet.example/meet",
    )
    assert m is not None
    row = m.inline_keyboard[0]
    assert [b.text for b in row] == [PORTAL_BUTTON_TEXT]
    assert row[0].url == "https://portal.example.com/calendar"


def test_notification_url_keyboard_rejects_hostile_meeting_scheme() -> None:
    m = notification_url_keyboard(
        "https://portal.example.com/calendar",
        meeting_url="javascript:alert(1)",
    )
    assert m is not None
    assert [b.text for b in m.inline_keyboard[0]] == [PORTAL_BUTTON_TEXT]


def test_notification_url_keyboard_without_meeting_is_portal_only() -> None:
    m = notification_url_keyboard("https://portal.example.com/calendar")
    assert m is not None
    assert [b.text for b in m.inline_keyboard[0]] == [PORTAL_BUTTON_TEXT]
