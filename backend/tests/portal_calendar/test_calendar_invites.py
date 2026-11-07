"""Accept invite-токенов EVENT / SHARE."""

from __future__ import annotations

import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from app.core.enums import CalendarInviteKind, CalendarMemberRole
from app.core.exceptions import UnauthorizedError
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_calendar import PortalCalendarAttendee
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.portal_calendar.conftest import (
    CALENDAR_API,
    as_invite_user,
    as_invite_user_b,
    as_user_b,
    assert_api_error,
    create_event,
    ensure_primary,
    seed_calendar_member,
    seed_invite_token,
    user_b_without_email,
)


async def test_accept_event_invite_marks_attendee_accepted(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cal = await ensure_primary(client_user)
    event = await create_event(
        client_user,
        cal["id"],
        attendees=[{"user_sub": "user-b"}],
    )
    token_row = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.EVENT,
        email="b@example.com",
        event_id=uuid.UUID(event["id"]),
        role=None,
    )

    with as_invite_user_b():
        r = await client_user.post(f"{CALENDAR_API}/invites/{token_row.token}/accept")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "event"
    assert body["event_id"] == event["id"]
    await sqlite_session.refresh(token_row)
    assert token_row.used_at is not None

    r = await client_user.get(f"{CALENDAR_API}/events/{event['id']}")
    assert r.status_code == 200, r.text
    att = next(a for a in r.json()["attendees"] if a["user_sub"] == "user-b")
    assert att["status"] == "accepted"


async def test_accept_event_invite_anonymous_ok(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Accept без optional user: обновляет attendee по email токена."""
    cal = await ensure_primary(client_user)
    event = await create_event(client_user, cal["id"])
    att = PortalCalendarAttendee(
        event_id=uuid.UUID(event["id"]),
        email="guest@example.com",
        user_sub=None,
        status="pending",
    )
    sqlite_session.add(att)
    await sqlite_session.commit()

    token_row = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.EVENT,
        email="guest@example.com",
        event_id=uuid.UUID(event["id"]),
        role=None,
    )
    r = await client_user.post(f"{CALENDAR_API}/invites/{token_row.token}/accept")
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "event"


async def test_accept_used_and_expired_invite(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cal = await ensure_primary(client_user)
    event = await create_event(client_user, cal["id"])
    event_id = uuid.UUID(event["id"])

    used = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.EVENT,
        email="user@example.com",
        event_id=event_id,
        used_at=now_utc(),
        role=None,
    )
    r = await client_user.post(f"{CALENDAR_API}/invites/{used.token}/accept")
    assert_api_error(r, 404, "not_found")

    expired = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.EVENT,
        email="user@example.com",
        event_id=event_id,
        expires_at=now_utc() - timedelta(hours=1),
        role=None,
    )
    r = await client_user.post(f"{CALENDAR_API}/invites/{expired.token}/accept")
    assert_api_error(r, 400, "bad_request")

    r = await client_user.post(f"{CALENDAR_API}/invites/not-a-real-token/accept")
    assert_api_error(r, 404, "not_found")


async def test_accept_event_invite_email_mismatch_403(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cal = await ensure_primary(client_user)
    event = await create_event(client_user, cal["id"])
    token_row = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.EVENT,
        email="other@example.com",
        event_id=uuid.UUID(event["id"]),
        role=None,
    )
    with as_invite_user_b():
        r = await client_user.post(f"{CALENDAR_API}/invites/{token_row.token}/accept")
    assert_api_error(r, 403, "forbidden")


async def test_accept_share_invite(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cal = await ensure_primary(client_user)
    token_row = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.SHARE,
        email="b@example.com",
        calendar_id=uuid.UUID(cal["id"]),
        role=CalendarMemberRole.EDITOR.value,
    )
    with as_invite_user_b():
        r = await client_user.post(f"{CALENDAR_API}/invites/{token_row.token}/accept")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["kind"] == "share"
        assert body["calendar_id"] == cal["id"]

    with as_user_b():
        r = await client_user.get(f"{CALENDAR_API}/calendars/{cal['id']}")
        assert r.status_code == 200, r.text
        assert r.json()["my_role"] == "editor"


async def test_accept_share_requires_auth(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """SHARE без пользователя (optional_current_user=None) → 400."""
    cal = await ensure_primary(client_user)
    token_row = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.SHARE,
        email="b@example.com",
        calendar_id=uuid.UUID(cal["id"]),
    )
    r = await client_user.post(f"{CALENDAR_API}/invites/{token_row.token}/accept")
    assert_api_error(r, 400, "bad_request")


async def test_accept_share_email_mismatch(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cal = await ensure_primary(client_user)
    token_row = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.SHARE,
        email="other@example.com",
        calendar_id=uuid.UUID(cal["id"]),
    )
    with as_invite_user_b():
        r = await client_user.post(f"{CALENDAR_API}/invites/{token_row.token}/accept")
    assert_api_error(r, 403, "forbidden")


@pytest.mark.asyncio
async def test_optional_auth_invalid_bearer_treated_as_anonymous(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    """Невалидный bearer → optional_current_user = None, не 401."""
    cal = await ensure_primary(client_user)
    event = await create_event(client_user, cal["id"])
    att = PortalCalendarAttendee(
        event_id=uuid.UUID(event["id"]),
        email="anon@example.com",
        user_sub=None,
        status="pending",
    )
    sqlite_session.add(att)
    await sqlite_session.commit()
    token_row = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.EVENT,
        email="anon@example.com",
        event_id=uuid.UUID(event["id"]),
        role=None,
    )

    with patch(
        "app.portal_calendar.routes.invites.verify_access_token",
        new_callable=AsyncMock,
        side_effect=UnauthorizedError("bad token"),
    ):
        r = await client_user.post(
            f"{CALENDAR_API}/invites/{token_row.token}/accept",
            headers={"Authorization": "Bearer garbage"},
        )
    assert r.status_code == 200, r.text
    assert r.json()["kind"] == "event"


async def test_accept_share_updates_existing_member(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cal = await ensure_primary(client_user)
    await seed_calendar_member(sqlite_session, cal["id"], "user-b", role="viewer", email="b@example.com")
    token_row = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.SHARE,
        email="b@example.com",
        calendar_id=uuid.UUID(cal["id"]),
        role=CalendarMemberRole.EDITOR.value,
    )
    with as_invite_user_b():
        r = await client_user.post(f"{CALENDAR_API}/invites/{token_row.token}/accept")
        assert r.status_code == 200, r.text
    with as_user_b():
        r = await client_user.get(f"{CALENDAR_API}/calendars/{cal['id']}")
        assert r.json()["my_role"] == "viewer"


async def test_accept_event_invite_without_attendee_does_not_burn_token(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cal = await ensure_primary(client_user)
    event = await create_event(client_user, cal["id"])
    token_row = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.EVENT,
        email="missing@example.com",
        event_id=uuid.UUID(event["id"]),
        role=None,
    )
    r = await client_user.post(f"{CALENDAR_API}/invites/{token_row.token}/accept")
    assert_api_error(r, 404, "not_found")
    await sqlite_session.refresh(token_row)
    assert token_row.used_at is None


async def test_accept_event_invite_empty_user_email_forbidden(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    cal = await ensure_primary(client_user)
    event = await create_event(client_user, cal["id"])
    token_row = await seed_invite_token(
        sqlite_session,
        kind=CalendarInviteKind.EVENT,
        email="guest@example.com",
        event_id=uuid.UUID(event["id"]),
        role=None,
    )
    with as_invite_user(user_b_without_email):
        r = await client_user.post(f"{CALENDAR_API}/invites/{token_row.token}/accept")
    assert_api_error(r, 403, "forbidden")
