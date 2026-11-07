from __future__ import annotations

import logging
import re
from datetime import date, datetime

logger = logging.getLogger(__name__)

_TELEGRAM_USERNAME_RE = re.compile(
    r"^(?:https?://)?(?:www\.)?(?:t\.me/|@)([A-Za-z0-9_]{5,32})$",
    re.IGNORECASE,
)
_TELEGRAM_BARE_USERNAME_RE = re.compile(r"^([A-Za-z0-9_]{5,32})$")
_DD_MM_YYYY_RE = re.compile(r"^\d{2}-\d{2}-\d{4}$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DD_DOT_MM_YYYY_RE = re.compile(r"^\d{2}\.\d{2}\.\d{4}$")


def normalize_telegram_from_sso(raw: str | None) -> str | None:
    """Канон: https://t.me/<username> в нижнем регистре."""
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    match = _TELEGRAM_USERNAME_RE.match(text)
    if not match:
        bare = _TELEGRAM_BARE_USERNAME_RE.match(text)
        if not bare:
            logger.warning("SSO telegram: не удалось распознать %r", raw[:80])
            return None
        username = bare.group(1).lower()
    else:
        username = match.group(1).lower()
    return f"https://t.me/{username}"


def parse_birthday_from_sso(raw: str | None) -> date | None:
    """Парсинг даты рождения из SSO; приоритет DD-MM-YYYY, затем ISO и DD.MM.YYYY."""
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        if _DD_MM_YYYY_RE.match(text):
            return datetime.strptime(text, "%d-%m-%Y").date()
        if _ISO_DATE_RE.match(text):
            return datetime.strptime(text, "%Y-%m-%d").date()
        if _DD_DOT_MM_YYYY_RE.match(text):
            return datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        logger.warning("SSO birthday: невалидная дата %r", raw)
        return None
    logger.warning("SSO birthday: неизвестный формат %r", raw)
    return None


def format_birthdate_for_ui(value: date | None) -> str:
    """Отображение даты в UI: DD-MM-YYYY."""
    if value is None:
        return "—"
    return value.strftime("%d-%m-%Y")
