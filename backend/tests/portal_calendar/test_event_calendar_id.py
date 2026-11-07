from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from tests.portal_calendar.conftest import CALENDAR_API, create_event, ensure_primary
from tests.portal_calendar.local_gateway import LocalCalendarGateway

_Seen = list[tuple[str, uuid.UUID | None]]


class _RecordingGateway(LocalCalendarGateway):
    def __init__(self, user: Any, seen: _Seen) -> None:
        super().__init__(user)
        self._seen = seen

    async def get_event(self, event_id: uuid.UUID, calendar_id: uuid.UUID | None = None) -> Any:
        self._seen.append(("get", calendar_id))
        return await super().get_event(event_id, calendar_id)

    async def update_event(
        self,
        event_id: uuid.UUID,
        payload: dict[str, Any],
        calendar_id: uuid.UUID | None = None,
    ) -> Any:
        self._seen.append(("update", calendar_id))
        return await super().update_event(event_id, payload, calendar_id)

    async def delete_event(self, event_id: uuid.UUID, calendar_id: uuid.UUID | None = None) -> None:
        self._seen.append(("delete", calendar_id))
        await super().delete_event(event_id, calendar_id)

    async def override_occurrence(
        self,
        event_id: uuid.UUID,
        payload: dict[str, Any],
        calendar_id: uuid.UUID | None = None,
    ) -> Any:
        self._seen.append(("override", calendar_id))
        return await super().override_occurrence(event_id, payload, calendar_id)


def _watching_remote(seen: _Seen):
    def require(user: Any, _authorization: str | None, _http: object) -> _RecordingGateway:
        return _RecordingGateway(user, seen)

    return require


async def test_event_routes_forward_calendar_id(
    client_user: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: _Seen = []
    monkeypatch.setattr("app.portal_calendar.routes.events.require_remote", _watching_remote(seen))
    calendar = await ensure_primary(client_user)
    event = await create_event(client_user, calendar["id"])
    event_id = event["id"]
    calendar_id = uuid.UUID(calendar["id"])
    query = {"calendar_id": calendar["id"]}

    direct = await client_user.get(f"{CALENDAR_API}/events/{event_id}", params=query)
    assert direct.status_code == 200, direct.text

    missing = await client_user.get(f"{CALENDAR_API}/events/{event_id}")
    assert missing.status_code == 200, missing.text

    patched = await client_user.patch(
        f"{CALENDAR_API}/events/{event_id}",
        params=query,
        json={"expected_version": event["version"], "title": "Перенос"},
    )
    assert patched.status_code == 200, patched.text

    moved = await client_user.post(
        f"{CALENDAR_API}/events/{event_id}/overrides",
        params=query,
        json={
            "original_start": "2026-11-06T10:00:00+00:00",
            "starts_at": "2026-11-07T10:00:00+00:00",
            "ends_at": "2026-11-07T11:00:00+00:00",
            "title": event["title"],
        },
    )
    assert moved.status_code == 200, moved.text

    deleted = await client_user.delete(f"{CALENDAR_API}/events/{event_id}", params=query)
    assert deleted.status_code == 204, deleted.text

    assert seen == [
        ("get", calendar_id),
        ("get", None),
        ("update", calendar_id),
        ("override", calendar_id),
        ("delete", calendar_id),
    ]
