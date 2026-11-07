"""Роуты календарей. Запись и чтение — в микросервисе."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Query

from app.api.deps import DbSession, HttpClient
from app.api.deps_auth import CurrentUser, PortalAdminUser
from app.portal_calendar.owner_labels import with_departments, with_owner_label, with_owner_labels
from app.portal_calendar.remote import require_remote
from app.portal_calendar.schemas.calendar import (
    CalendarCreate,
    CalendarRead,
    CalendarShowUpdate,
    CalendarUpdate,
    PeerCalendarContextRead,
)
from app.portal_calendar.visibility import owned_calendars, shown_to_other_departments

router = APIRouter(prefix="/portal/calendar/calendars", tags=["Портал · Календарь"])


@router.get("/peer-context", response_model=PeerCalendarContextRead)
async def api_peer_calendar_context(
    user: CurrentUser,
    http: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
    user_sub: str = Query(description="sub владельца календаря для cross-create"),
) -> PeerCalendarContextRead:
    calendar = await require_remote(user, authorization, http).primary_for(user_sub.strip())
    return PeerCalendarContextRead(calendar_id=calendar.id, owner_sub=calendar.owner_sub)


@router.get("", response_model=list[CalendarRead])
async def api_list_calendars(
    user: CurrentUser,
    http: HttpClient,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> list[CalendarRead]:
    # Без PagedResponse: на экране только свои календари, не лента отдела.
    rows = await require_remote(user, authorization, http).list_calendars()
    return await with_owner_labels(db, owned_calendars(rows, user.sub))


@router.get("/shared", response_model=list[CalendarRead])
async def api_list_shared_calendars(
    user: PortalAdminUser,
    http: HttpClient,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> list[CalendarRead]:
    # Без PagedResponse: только календари с галочкой показа другим отделам.
    rows = await require_remote(user, authorization, http).list_calendars()
    return await with_departments(db, shown_to_other_departments(rows))


@router.post("", response_model=CalendarRead, status_code=201)
async def api_create_calendar(
    body: CalendarCreate,
    user: CurrentUser,
    http: HttpClient,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> CalendarRead:
    created = await require_remote(user, authorization, http).create_calendar(
        body.model_dump(mode="json", exclude_none=True),
    )
    return await with_owner_label(db, created)


@router.get("/{calendar_id}", response_model=CalendarRead)
async def api_get_calendar(
    calendar_id: uuid.UUID,
    user: CurrentUser,
    http: HttpClient,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> CalendarRead:
    row = await require_remote(user, authorization, http).get_calendar(calendar_id)
    return await with_owner_label(db, row)


@router.patch("/{calendar_id}/show", response_model=CalendarRead)
async def api_set_calendar_show(
    calendar_id: uuid.UUID,
    body: CalendarShowUpdate,
    user: PortalAdminUser,
    http: HttpClient,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> CalendarRead:
    row = await require_remote(user, authorization, http).set_show(calendar_id, body.enabled)
    return await with_owner_label(db, row)


@router.patch("/{calendar_id}", response_model=CalendarRead)
async def api_update_calendar(
    calendar_id: uuid.UUID,
    body: CalendarUpdate,
    user: CurrentUser,
    http: HttpClient,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> CalendarRead:
    row = await require_remote(user, authorization, http).update_calendar(
        calendar_id,
        body.model_dump(mode="json", exclude_unset=True),
    )
    return await with_owner_label(db, row)


@router.delete("/{calendar_id}", status_code=204)
async def api_delete_calendar(
    calendar_id: uuid.UUID,
    user: CurrentUser,
    http: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
) -> None:
    await require_remote(user, authorization, http).delete_calendar(calendar_id)
