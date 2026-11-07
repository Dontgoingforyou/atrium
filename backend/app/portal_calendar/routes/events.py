"""Роуты событий календаря. Запись и чтение — в микросервисе."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Header, Query

from app.api.deps import DbSession, HttpClient
from app.api.deps_auth import CurrentUser
from app.core.portal_search_constants import PORTAL_SEARCH_MIN_QUERY_LEN
from app.portal_calendar.remote import attendee_bodies, require_remote
from app.portal_calendar.schemas.calendar import (
    AttendeeCreate,
    AttendeeRead,
    CalendarEventSearchHitRead,
    EventCreate,
    EventOccurrenceOverride,
    EventOccurrenceRead,
    EventRead,
    EventUpdate,
)
from app.portal_calendar.services._access import find_profile_by_sub
from app.portal_search.services import embedding as emb_svc
from app.portal_search.services.entity_text import calendar_event_meta, calendar_event_to_text
from app.schemas.pagination import PagedResponse

router = APIRouter(prefix="/portal/calendar", tags=["Портал · Календарь"])


async def _remote_event_body(db: DbSession, body: EventCreate | EventUpdate) -> dict[str, Any]:
    data = body.model_dump(mode="json", exclude_unset=True)
    data.pop("calendar_id", None)
    attendees = data.get("attendees")
    if attendees is not None:
        data["attendees"] = await attendee_bodies(db, attendees)
    return data


@router.get("/occurrences", response_model=list[EventOccurrenceRead])
async def api_list_occurrences(
    user: CurrentUser,
    http: HttpClient,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
    from_dt: datetime = Query(alias="from"),
    to_dt: datetime = Query(alias="to"),
    calendar_id: list[uuid.UUID] | None = Query(default=None),
    user_sub: str | None = Query(
        default=None,
        description="Сетка участника: его календари и события, куда его пригласили",
    ),
) -> list[EventOccurrenceRead]:
    peer = (user_sub or "").strip() or None
    peer_email = None
    if peer:
        profile = await find_profile_by_sub(db, peer)
        if profile is not None and profile.email:
            peer_email = profile.email
    return await require_remote(user, authorization, http).list_occurrences(
        starts=from_dt,
        ends=to_dt,
        calendar_ids=calendar_id,
        peer_user_sub=peer,
        peer_email=peer_email,
    )


@router.get(
    "/events/search",
    summary="Поиск событий календаря",
    response_model=PagedResponse[CalendarEventSearchHitRead],
)
async def api_search_events(
    user: CurrentUser,
    http: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
    q: str = Query(min_length=PORTAL_SEARCH_MIN_QUERY_LEN, max_length=500),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> PagedResponse[CalendarEventSearchHitRead]:
    items, total = await require_remote(user, authorization, http).search_events(q, skip, limit)
    return PagedResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("/events", response_model=EventRead, status_code=201)
async def api_create_event(
    body: EventCreate,
    user: CurrentUser,
    db: DbSession,
    bg: BackgroundTasks,
    http: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
) -> EventRead:
    result = await require_remote(user, authorization, http).create_event(
        body.calendar_id,
        await _remote_event_body(db, body),
    )
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        "calendar_event",
        str(result.id),
        calendar_event_to_text(result.title, result.description, result.location),
        calendar_event_meta(calendar_id=str(result.calendar_id), organizer_sub=result.organizer_sub),
    )
    return result


@router.get("/events/{event_id}", response_model=EventRead)
async def api_get_event(
    event_id: uuid.UUID,
    user: CurrentUser,
    http: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
    calendar_id: uuid.UUID | None = Query(default=None),
) -> EventRead:
    return await require_remote(user, authorization, http).get_event(event_id, calendar_id)


@router.patch("/events/{event_id}", response_model=EventRead)
async def api_update_event(
    event_id: uuid.UUID,
    body: EventUpdate,
    user: CurrentUser,
    db: DbSession,
    bg: BackgroundTasks,
    http: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
    calendar_id: uuid.UUID | None = Query(default=None),
) -> EventRead:
    result = await require_remote(user, authorization, http).update_event(
        event_id,
        await _remote_event_body(db, body),
        calendar_id,
    )
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        "calendar_event",
        str(result.id),
        calendar_event_to_text(result.title, result.description, result.location),
        calendar_event_meta(calendar_id=str(result.calendar_id), organizer_sub=result.organizer_sub),
    )
    return result


@router.delete("/events/{event_id}", status_code=204)
async def api_delete_event(
    event_id: uuid.UUID,
    user: CurrentUser,
    bg: BackgroundTasks,
    http: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
    calendar_id: uuid.UUID | None = Query(default=None),
) -> None:
    await require_remote(user, authorization, http).delete_event(event_id, calendar_id)
    bg.add_task(emb_svc.delete_embedding_bg, "calendar_event", str(event_id))


@router.post("/events/{event_id}/overrides", response_model=EventRead)
async def api_upsert_override(
    event_id: uuid.UUID,
    body: EventOccurrenceOverride,
    user: CurrentUser,
    http: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
    calendar_id: uuid.UUID | None = Query(default=None),
) -> EventRead:
    return await require_remote(user, authorization, http).override_occurrence(
        event_id,
        body.model_dump(mode="json"),
        calendar_id,
    )


@router.post("/events/{event_id}/attendees", response_model=AttendeeRead, status_code=201)
async def api_add_attendee(
    event_id: uuid.UUID,
    body: AttendeeCreate,
    user: CurrentUser,
    db: DbSession,
    http: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
) -> AttendeeRead:
    payloads = await attendee_bodies(db, [{"user_sub": body.user_sub}])
    return await require_remote(user, authorization, http).add_attendee(event_id, payloads[0])


@router.delete("/events/{event_id}/attendees/{attendee_id}", status_code=204)
async def api_remove_attendee(
    event_id: uuid.UUID,
    attendee_id: uuid.UUID,
    user: CurrentUser,
    http: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    await require_remote(user, authorization, http).remove_attendee(event_id, attendee_id)
