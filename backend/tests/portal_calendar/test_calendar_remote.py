"""Преобразование ответа микросервиса в форму экрана Космолета."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from app.core.exceptions import NotFoundError
from app.portal_calendar.remote import (
    CalendarRemote,
    calendar_from_remote,
    calendar_remote_for_search,
    event_from_remote,
    occurrence_from_remote,
    occurrence_kept_on_peer_grid,
    remote_event_search_query_fits,
)
from tests.helpers.portal_test_users import user_portal_regular


def test_calendar_owner_role_follows_sub() -> None:
    calendar_id = uuid.uuid4()
    raw = {
        "id": str(calendar_id),
        "owner_sub": "me",
        "title": "Мой",
        "color": "#3B82F6",
        "timezone": "UTC",
        "is_primary": True,
        "show_to_other_departments": True,
    }
    own = calendar_from_remote(raw, "me")
    foreign = calendar_from_remote(raw, "other")
    assert own.my_role == "owner"
    assert own.show_to_other_departments is True
    assert foreign.my_role == "viewer"
    assert own.id == calendar_id
    assert own.members == []


def test_sso_owner_is_the_portal_user() -> None:
    raw = {
        "id": str(uuid.uuid4()),
        "owner_sub": "keycloak-sub",
        "title": "Новый",
        "color": "#3B82F6",
        "timezone": "UTC",
        "is_primary": False,
    }
    own = calendar_from_remote(raw, "portal-sub", {"keycloak-sub"})
    assert own.my_role == "owner"
    assert own.owner_sub == "portal-sub"


def test_event_keeps_version_and_attendees() -> None:
    raw = {
        "id": str(uuid.uuid4()),
        "calendar_id": str(uuid.uuid4()),
        "organizer_sub": "me",
        "title": "Созвон",
        "description": None,
        "location": None,
        "starts_at": "2026-10-27T09:00:00+00:00",
        "ends_at": None,
        "timezone": "UTC",
        "rrule": None,
        "color": None,
        "version": 3,
        "attendees": [
            {"id": str(uuid.uuid4()), "email": "a@example.com", "user_sub": "me", "status": "accepted"},
        ],
        "reminders": [{"id": str(uuid.uuid4()), "offset_minutes": 15, "channel": "portal"}],
    }
    event = event_from_remote(raw)
    assert event.version == 3
    assert event.ends_at is None
    assert event.attendees[0].email == "a@example.com"
    assert event.reminders[0].offset_minutes == 15
    assert event.starts_at == datetime(2026, 10, 27, 9, 0, tzinfo=UTC)


def test_occurrence_of_another_owner_is_peer_view() -> None:
    raw = {
        "event_id": str(uuid.uuid4()),
        "calendar_id": str(uuid.uuid4()),
        "calendar_color": "#3B82F6",
        "color": None,
        "original_start": "2026-10-27T09:00:00Z",
        "starts_at": "2026-10-27T09:00:00Z",
        "ends_at": None,
        "title": "Чужое",
        "description": None,
        "location": None,
        "timezone": "UTC",
        "rrule": None,
        "organizer_sub": "owner",
        "attendees": [],
        "reminders": [],
    }
    own = occurrence_from_remote(raw, owner_sub="me", user_sub="me")
    peer = occurrence_from_remote(raw, owner_sub="owner", user_sub="me")
    assert own.is_peer_view is False
    assert peer.is_peer_view is True
    assert peer.is_cancelled is False


def test_closed_calendar_is_omitted_from_portal_search(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.portal_calendar.remote.get_settings",
        lambda: SimpleNamespace(calendar_service_url="http://calendar.test", calendar_product=""),
    )
    remote, omit = calendar_remote_for_search(user_portal_regular(), "Bearer token", MagicMock())
    assert remote is None
    assert omit is True


def test_event_search_query_limit_is_the_remote_max() -> None:
    assert remote_event_search_query_fits("а" * 200) is True
    assert remote_event_search_query_fits("а" * 201) is False


async def test_event_search_keeps_query_and_caps_page() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.path == "/calendars":
            return httpx.Response(200, json={"items": [], "total": 0, "skip": 0, "limit": 200})
        return httpx.Response(200, json={"items": [], "total": 0, "skip": 0, "limit": 100})

    transport = httpx.MockTransport(handler)
    query = "а" * 250
    async with httpx.AsyncClient(transport=transport) as client:
        remote = CalendarRemote(client, "http://calendar.test", "token", "10", "user-sub", "cosmolet")
        await remote.search_events("созвон", 0, 108)
        await remote.search_events(query, 0, 20)

    search_calls = [request for request in calls if request.url.path.endswith("/events/search")]
    assert search_calls[0].url.params["q"] == "созвон"
    assert search_calls[0].url.params["limit"] == "100"
    assert search_calls[1].url.params["q"] == query
    assert search_calls[1].url.params["limit"] == "20"


def _remote_event(event_id: uuid.UUID, calendar_id: uuid.UUID) -> dict[str, object]:
    return {
        "id": str(event_id),
        "calendar_id": str(calendar_id),
        "organizer_sub": "user-sub",
        "title": "Созвон",
        "description": None,
        "location": None,
        "starts_at": "2026-11-03T14:00:00+00:00",
        "ends_at": "2026-11-03T15:00:00+00:00",
        "timezone": "UTC",
        "rrule": None,
        "color": None,
        "version": 2,
        "attendees": [],
        "reminders": [],
    }


async def test_known_calendar_does_not_scan_every_calendar() -> None:
    calendar_id = uuid.uuid4()
    event_id = uuid.uuid4()
    paths: list[str] = []
    direct = f"/calendars/{calendar_id}/events/{event_id}"

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.method in {"DELETE", "POST"}:
            return httpx.Response(204)
        return httpx.Response(200, json=_remote_event(event_id, calendar_id))

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        remote = CalendarRemote(client, "http://calendar.test", "token", "10", "user-sub", "cosmolet")
        await remote.get_event(event_id, calendar_id)
        await remote.update_event(event_id, {"title": "Перенос", "expected_version": 2}, calendar_id)
        await remote.override_occurrence(
            event_id,
            {"original_start": "2026-11-03T14:00:00+00:00", "title": "Перенос"},
            calendar_id,
        )
        await remote.delete_event(event_id, calendar_id)

    assert paths == [direct, direct, f"{direct}/overrides", direct, direct]
    assert "/calendars" not in paths


async def test_missing_calendar_id_still_scans_the_list() -> None:
    paths: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        return httpx.Response(200, json={"items": [], "total": 0, "skip": 0, "limit": 200})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        remote = CalendarRemote(client, "http://calendar.test", "token", "10", "user-sub", "cosmolet")
        with pytest.raises(NotFoundError, match="Событие не найдено"):
            await remote.get_event(uuid.uuid4())

    assert paths == ["/calendars"]


def test_peer_grid_keeps_invite_and_drops_the_rest() -> None:
    attendees = [{"email": "diana@example.com", "user_sub": "diana"}]
    assert occurrence_kept_on_peer_grid(
        owner_sub="kseniya",
        raw_owner_sub="kseniya",
        peer_user_sub="diana",
        attendees=attendees,
        peer_email="diana@example.com",
    )
    assert occurrence_kept_on_peer_grid(
        owner_sub="kseniya",
        raw_owner_sub="kseniya",
        peer_user_sub="diana",
        attendees=[{"email": "Diana@Example.com", "user_sub": None}],
        peer_email="diana@example.com",
    )
    assert occurrence_kept_on_peer_grid(
        owner_sub="diana",
        raw_owner_sub="diana",
        peer_user_sub="diana",
        attendees=[],
        peer_email=None,
    )
    assert not occurrence_kept_on_peer_grid(
        owner_sub="kseniya",
        raw_owner_sub="kseniya",
        peer_user_sub="diana",
        attendees=[{"email": "other@example.com", "user_sub": "other"}],
        peer_email="diana@example.com",
    )


def _remote_calendar(calendar_id: uuid.UUID, owner: str) -> dict[str, object]:
    return {
        "id": str(calendar_id),
        "owner_sub": owner,
        "title": owner,
        "color": "#3B82F6",
        "timezone": "UTC",
        "is_primary": True,
        "show_to_other_departments": False,
    }


def _remote_occurrence(
    calendar_id: uuid.UUID,
    title: str,
    attendees: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "event_id": str(uuid.uuid4()),
        "calendar_id": str(calendar_id),
        "calendar_color": "#3B82F6",
        "color": None,
        "original_start": "2026-11-04T07:00:00Z",
        "starts_at": "2026-11-04T07:00:00Z",
        "ends_at": "2026-11-04T08:00:00Z",
        "title": title,
        "description": None,
        "location": None,
        "timezone": "UTC",
        "rrule": None,
        "organizer_sub": "kseniya",
        "attendees": attendees,
        "reminders": [],
    }


async def test_peer_grid_lists_invite_on_someone_elses_calendar() -> None:
    kseniya_id = uuid.uuid4()
    diana_id = uuid.uuid4()
    calendars = [_remote_calendar(kseniya_id, "kseniya"), _remote_calendar(diana_id, "diana")]
    rows = [
        _remote_occurrence(
            kseniya_id,
            "тест",
            [{"id": str(uuid.uuid4()), "email": "diana@example.com", "user_sub": "diana", "status": "accepted"}],
        ),
        _remote_occurrence(kseniya_id, "личное", []),
        _remote_occurrence(diana_id, "дейли", []),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/calendars":
            return httpx.Response(200, json={"items": calendars, "total": len(calendars), "skip": 0, "limit": 200})
        return httpx.Response(200, json=rows)

    transport = httpx.MockTransport(handler)
    window = datetime(2026, 11, 1, tzinfo=UTC)
    async with httpx.AsyncClient(transport=transport) as client:
        remote = CalendarRemote(client, "http://calendar.test", "token", "10", "kseniya", "cosmolet")
        found = await remote.list_occurrences(
            starts=window,
            ends=datetime(2026, 12, 1, tzinfo=UTC),
            calendar_ids=None,
            peer_user_sub="diana",
            peer_email="diana@example.com",
        )

    assert [item.title for item in found] == ["тест", "дейли"]
