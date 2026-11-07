"""Фасад сервисов календаря."""

from __future__ import annotations

from app.portal_calendar.services._attendees import (
    accept_invite_token,
    add_attendee,
    remove_attendee,
)
from app.portal_calendar.services._calendars import (
    create_calendar,
    delete_calendar,
    ensure_primary_calendar,
    get_calendar,
    get_peer_calendar_context,
    list_calendars,
    update_calendar,
)
from app.portal_calendar.services._events import (
    create_event,
    delete_event,
    get_event,
    list_occurrences,
    update_event,
    upsert_occurrence_override,
)
from app.portal_calendar.services._search import accessible_calendar_event_ids, search_events

__all__ = [
    "accept_invite_token",
    "accessible_calendar_event_ids",
    "add_attendee",
    "create_calendar",
    "create_event",
    "delete_calendar",
    "delete_event",
    "ensure_primary_calendar",
    "get_calendar",
    "get_peer_calendar_context",
    "get_event",
    "list_calendars",
    "list_occurrences",
    "remove_attendee",
    "search_events",
    "update_calendar",
    "update_event",
    "upsert_occurrence_override",
]
