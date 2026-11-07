"""Первый http(s)-URL встречи: сначала «Место», затем описание."""

from __future__ import annotations

import re

_HTTP_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
_TRAILING_PUNCT = ".,;:!?)"
_JOIN_NOTIFICATION_TYPES = frozenset(
    {"calendar_invite", "calendar_reminder", "calendar_event_updated"},
)


def first_http_url(*texts: str | None) -> str | None:
    """Первый http/https URL по порядку аргументов; прочие схемы отбросить."""
    for text in texts:
        if not text:
            continue
        for match in _HTTP_URL_RE.finditer(text):
            url = match.group(0)
            while url and url[-1] in _TRAILING_PUNCT:
                url = url[:-1]
            lowered = url.lower()
            if lowered.startswith(("http://", "https://")):
                return url
    return None


def calendar_meeting_http_url(
    *,
    location: str | None,
    description: str | None,
) -> str | None:
    """Ссылка на встречу: location важнее description."""
    return first_http_url(location, description)


def calendar_meeting_http_url_from_event(event: object | None) -> str | None:
    if event is None:
        return None
    location = getattr(event, "location", None)
    description = getattr(event, "description", None)
    return calendar_meeting_http_url(
        location=location if isinstance(location, str) else None,
        description=description if isinstance(description, str) else None,
    )


def calendar_meeting_url_for_notification(notif: object) -> str | None:
    if getattr(notif, "type", None) not in _JOIN_NOTIFICATION_TYPES:
        return None
    event = getattr(notif, "calendar_event", None)
    return calendar_meeting_http_url_from_event(event)
