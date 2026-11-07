from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Лимиты Bot API
_MAX_BUTTON_TEXT = 64
_MAX_URL_LEN = 2048

PORTAL_BUTTON_TEXT = "Открыть в портале"
JOIN_BUTTON_TEXT = "Подключиться"


def _https_button(url: str, button_text: str, *, empty_fallback: str = "Открыть") -> InlineKeyboardButton | None:
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        return None
    # Только https — иначе Telegram отклонит кнопку (локальная разработка на http).
    if u.startswith("http://"):
        return None
    if len(u) > _MAX_URL_LEN:
        u = u[:_MAX_URL_LEN]
    label = (button_text or empty_fallback).strip()[:_MAX_BUTTON_TEXT] or empty_fallback
    return InlineKeyboardButton(text=label, url=u)


def inline_url_keyboard(url: str, button_text: str = PORTAL_BUTTON_TEXT) -> InlineKeyboardMarkup | None:
    button = _https_button(url, button_text)
    if button is None:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def notification_url_keyboard(
    portal_url: str,
    *,
    meeting_url: str | None = None,
    portal_button_text: str = PORTAL_BUTTON_TEXT,
) -> InlineKeyboardMarkup | None:
    """Ряд кнопок: «Подключиться» (https-встреча) и «Открыть в портале»."""
    buttons: list[InlineKeyboardButton] = []
    if meeting_url:
        join = _https_button(meeting_url, JOIN_BUTTON_TEXT)
        if join is not None:
            buttons.append(join)
    portal = _https_button(portal_url, portal_button_text)
    if portal is not None:
        buttons.append(portal)
    if not buttons:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def body_with_fallback_link(
    body: str,
    url: str,
    markup: InlineKeyboardMarkup | None,
    *,
    fallback_anchor_text: str = "Открыть",
) -> tuple[str, str | None]:
    """Текст и ``parse_mode`` для ``send_message``.

    Если inline-кнопка есть — тело без разметки, ``parse_mode=None``.
    Если кнопки нет — в конец добавляется строка с **полным URL** в открытом виде
    (``👉 <подпись>: <url>``), ``parse_mode=None``. HTML-``<a>`` для ``http://`` в ряде
    клиентов не даёт клика — явный URL надёжнее для копирования и локальной отладки.
    """
    if markup is not None:
        return (body, None)
    u = url.strip()
    if len(u) > _MAX_URL_LEN:
        u = u[:_MAX_URL_LEN]
    label = (fallback_anchor_text.strip() or "Открыть").strip()
    link_line = f"👉 {label}: {u}"
    return (f"{body}\n\n{link_line}", None)
