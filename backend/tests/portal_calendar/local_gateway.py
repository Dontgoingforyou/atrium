"""Подмена микросервиса в тестах: экранные ручки зовут те же местные функции, что поиск и MCP."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.api.deps import get_db_session
from app.main import app
from app.portal_calendar.schemas.calendar import (
    CalendarCreate,
    CalendarEventSearchHitRead,
    CalendarUpdate,
    EventCreate,
    EventOccurrenceOverride,
    EventRead,
    EventUpdate,
)
from app.portal_calendar.services import (
    add_attendee,
    create_calendar,
    create_event,
    delete_calendar,
    delete_event,
    get_calendar,
    get_event,
    get_peer_calendar_context,
    list_calendars,
    list_occurrences,
    remove_attendee,
    search_events,
    update_calendar,
    update_event,
    upsert_occurrence_override,
)
from app.schemas.auth import UserPublic
from sqlalchemy.ext.asyncio import AsyncSession


async def _session() -> AsyncSession:
    agen = app.dependency_overrides[get_db_session]()
    try:
        return await anext(agen)
    finally:
        await agen.aclose()


_show_flags: dict[uuid.UUID, bool] = {}


def _with_show(row: Any) -> Any:
    enabled = _show_flags.get(row.id)
    if enabled is None:
        return row
    return row.model_copy(update={"show_to_other_departments": enabled})


class LocalCalendarGateway:
    def __init__(self, user: UserPublic) -> None:
        self._user = user

    async def list_calendars(self) -> list[Any]:
        rows = await list_calendars(await _session(), self._user)
        return [_with_show(row) for row in rows]

    async def set_show(self, calendar_id: uuid.UUID, enabled: bool) -> Any:
        calendar = await get_calendar(await _session(), self._user, calendar_id)
        _show_flags[calendar_id] = enabled
        return calendar.model_copy(update={"show_to_other_departments": enabled})

    async def primary_for(self, owner_sub: str) -> Any:
        ctx = await get_peer_calendar_context(await _session(), self._user, owner_sub)
        return type("Primary", (), {"id": ctx.calendar_id, "owner_sub": ctx.owner_sub})()

    async def create_calendar(self, payload: dict[str, Any]) -> Any:
        return await create_calendar(await _session(), self._user, CalendarCreate.model_validate(payload))

    async def get_calendar(self, calendar_id: uuid.UUID) -> Any:
        return await get_calendar(await _session(), self._user, calendar_id)

    async def update_calendar(self, calendar_id: uuid.UUID, payload: dict[str, Any]) -> Any:
        return await update_calendar(
            await _session(),
            self._user,
            calendar_id,
            CalendarUpdate.model_validate(payload),
        )

    async def delete_calendar(self, calendar_id: uuid.UUID) -> None:
        await delete_calendar(await _session(), self._user, calendar_id)

    async def list_occurrences(
        self,
        *,
        starts: datetime,
        ends: datetime,
        calendar_ids: list[uuid.UUID] | None,
        peer_user_sub: str | None,
    ) -> list[Any]:
        return await list_occurrences(
            await _session(),
            self._user,
            window_start=starts,
            window_end=ends,
            calendar_ids=calendar_ids,
            peer_user_sub=peer_user_sub,
        )

    async def search_events(self, q: str, skip: int, limit: int) -> tuple[list[CalendarEventSearchHitRead], int]:
        items, total = await search_events(await _session(), self._user, q, skip=skip, limit=limit)
        hits = [CalendarEventSearchHitRead.model_validate(item, from_attributes=True) for item in items]
        return hits, total

    async def create_event(self, calendar_id: uuid.UUID, payload: dict[str, Any]) -> EventRead:
        data = dict(payload)
        data["calendar_id"] = calendar_id
        return await create_event(await _session(), self._user, EventCreate.model_validate(data))

    async def get_event(self, event_id: uuid.UUID, calendar_id: uuid.UUID | None = None) -> EventRead:
        del calendar_id
        return await get_event(await _session(), self._user, event_id)

    async def update_event(
        self,
        event_id: uuid.UUID,
        payload: dict[str, Any],
        calendar_id: uuid.UUID | None = None,
    ) -> EventRead:
        del calendar_id
        return await update_event(await _session(), self._user, event_id, EventUpdate.model_validate(payload))

    async def delete_event(self, event_id: uuid.UUID, calendar_id: uuid.UUID | None = None) -> None:
        del calendar_id
        await delete_event(await _session(), self._user, event_id)

    async def add_attendee(self, event_id: uuid.UUID, payload: dict[str, str | None]) -> Any:
        user_sub = payload.get("user_sub")
        if not user_sub:
            raise ValueError("user_sub")
        return await add_attendee(await _session(), self._user, event_id, user_sub)

    async def remove_attendee(self, event_id: uuid.UUID, attendee_id: uuid.UUID) -> None:
        await remove_attendee(await _session(), self._user, event_id, attendee_id)

    async def override_occurrence(
        self,
        event_id: uuid.UUID,
        payload: dict[str, Any],
        calendar_id: uuid.UUID | None = None,
    ) -> EventRead:
        del calendar_id
        return await upsert_occurrence_override(
            await _session(),
            self._user,
            event_id,
            EventOccurrenceOverride.model_validate(payload),
        )


def local_remote(user: UserPublic, _authorization: str | None, _http: object) -> LocalCalendarGateway:
    return LocalCalendarGateway(user)
