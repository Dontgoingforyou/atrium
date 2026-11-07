"""Публичное принятие invite-токена календаря."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header

from app.api.deps import DbSession, HttpClient
from app.api.deps_auth import extract_bearer_token, verify_access_token
from app.core.exceptions import AppError
from app.portal_calendar.schemas.calendar import InviteTokenAcceptResponse
from app.portal_calendar.services import accept_invite_token
from app.schemas.auth import UserPublic

router = APIRouter(prefix="/portal/calendar/invites", tags=["Портал · Календарь"])


async def optional_current_user(
    db: DbSession,
    http_client: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
) -> UserPublic | None:
    token = extract_bearer_token(authorization)
    if token is None:
        return None
    try:
        return await verify_access_token(token, db, http_client)
    except AppError:
        return None


@router.post("/{token}/accept", response_model=InviteTokenAcceptResponse)
async def api_accept_invite(
    token: str,
    db: DbSession,
    user: Annotated[UserPublic | None, Depends(optional_current_user)],
) -> InviteTokenAcceptResponse:
    kind, calendar_id, event_id = await accept_invite_token(db, token, user=user)
    return InviteTokenAcceptResponse(
        kind=kind,
        calendar_id=calendar_id,
        event_id=event_id,
        message="Приглашение принято",
    )
