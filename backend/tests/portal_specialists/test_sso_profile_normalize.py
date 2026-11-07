from datetime import date

from app.portal_specialists.services.sso_profile_normalize import (
    format_birthdate_for_ui,
    normalize_telegram_from_sso,
    parse_birthday_from_sso,
)


def test_normalize_telegram_full_url() -> None:
    assert normalize_telegram_from_sso("https://t.me/dontgoingforyou") == "https://t.me/dontgoingforyou"


def test_normalize_telegram_at_username() -> None:
    assert normalize_telegram_from_sso("@DontGoingForYou") == "https://t.me/dontgoingforyou"


def test_normalize_telegram_bare_username() -> None:
    assert normalize_telegram_from_sso("dontgoingforyou") == "https://t.me/dontgoingforyou"


def test_normalize_telegram_invalid() -> None:
    assert normalize_telegram_from_sso("not-a-telegram") is None
    assert normalize_telegram_from_sso("") is None


def test_parse_birthday_dd_mm_yyyy() -> None:
    assert parse_birthday_from_sso("20-06-1998") == date(1998, 6, 20)


def test_parse_birthday_iso() -> None:
    assert parse_birthday_from_sso("1998-06-20") == date(1998, 6, 20)


def test_parse_birthday_invalid() -> None:
    assert parse_birthday_from_sso("32-13-1999") is None


def test_format_birthdate_for_ui() -> None:
    assert format_birthdate_for_ui(date(1998, 6, 20)) == "20-06-1998"
