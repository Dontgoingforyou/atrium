"""Фикстуры и хелперы для тестов portal_calendar."""

from __future__ import annotations

import secrets
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from app.api.deps_auth import get_current_user
from app.core.auth_constants import SSO_GID_OUTSTAFF
from app.core.enums import CalendarInviteKind, CalendarMemberRole
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_calendar import PortalCalendarInviteToken, PortalCalendarMember
from app.main import app
from app.schemas.auth import UserPublic
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession
from tests.helpers.portal_test_users import user_portal_user_b

CALENDAR_API = "/api/v1/portal/calendar"


def assert_api_error(response: Response, status: int, code: str) -> None:
    """Ошибка AppError: и HTTP-статус, и контрактный `code`."""
    assert response.status_code == status, response.text
    assert response.json()["code"] == code


def user_b_without_email() -> UserPublic:
    """user-b с пустым email (mismatch invite)."""
    return UserPublic(
        sub="user-b",
        email="",
        username="ub",
        full_name="User B",
        idp_groups=["outstaff"],
        is_portal_admin=False,
        gid_number=SSO_GID_OUTSTAFF,
    )


@contextmanager
def override_dependency(dependency: object, override: object) -> Iterator[None]:
    """Подменить Depends без `dependency_overrides.clear()`."""
    previous = app.dependency_overrides.get(dependency)
    app.dependency_overrides[dependency] = override
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[dependency] = previous
        else:
            app.dependency_overrides.pop(dependency, None)


@contextmanager
def as_user(user_factory: Callable[[], UserPublic]) -> Iterator[None]:
    """Временно подменить get_current_user (client_user / client_user_b нельзя комбинировать)."""
    previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = user_factory
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[get_current_user] = previous
        else:
            app.dependency_overrides.pop(get_current_user, None)


@contextmanager
def as_user_b() -> Iterator[None]:
    with as_user(user_portal_user_b):
        yield


@contextmanager
def as_invite_user(user_factory: Callable[[], UserPublic]) -> Iterator[None]:
    """Подмена optional_current_user для POST /invites/.../accept."""
    from app.portal_calendar.routes.invites import optional_current_user

    previous = app.dependency_overrides.get(optional_current_user)
    app.dependency_overrides[optional_current_user] = user_factory
    try:
        yield
    finally:
        if previous is not None:
            app.dependency_overrides[optional_current_user] = previous
        else:
            app.dependency_overrides.pop(optional_current_user, None)


@contextmanager
def as_invite_user_b() -> Iterator[None]:
    with as_invite_user(user_portal_user_b):
        yield


async def ensure_primary(client: AsyncClient) -> dict[str, Any]:
    """GET /calendars → основной календарь текущего пользователя."""
    r = await client.get(f"{CALENDAR_API}/calendars")
    assert r.status_code == 200, r.text
    items = r.json()
    primary = next((c for c in items if c["is_primary"]), None)
    assert primary is not None, "primary calendar missing"
    return primary


async def create_event(
    client: AsyncClient,
    calendar_id: str | uuid.UUID,
    **kwargs: Any,
) -> dict[str, Any]:
    """Создать событие через API и вернуть JSON."""
    starts = kwargs.pop("starts_at", None)
    if starts is None:
        starts = datetime.now(UTC) + timedelta(days=1)
        starts = starts.replace(hour=10, minute=0, second=0, microsecond=0)
    ends = kwargs.pop("ends_at", starts + timedelta(hours=1) if starts else None)
    attendees = kwargs.pop("attendees", None)
    if attendees is None:
        organizer_sub = kwargs.pop("organizer_sub", "user-sub")
        attendees = [{"user_sub": organizer_sub}]
    else:
        kwargs.pop("organizer_sub", None)
    payload: dict[str, Any] = {
        "calendar_id": str(calendar_id),
        "title": kwargs.pop("title", "Тестовое событие"),
        "starts_at": starts.isoformat() if hasattr(starts, "isoformat") else starts,
        "timezone": "UTC",
        "attendees": attendees,
        **kwargs,
    }
    if ends is not None and "ends_at" not in payload:
        payload["ends_at"] = ends.isoformat() if hasattr(ends, "isoformat") else ends
    r = await client.post(f"{CALENDAR_API}/events", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


async def seed_calendar_member(
    session: AsyncSession,
    calendar_id: str | uuid.UUID,
    user_sub: str,
    *,
    role: str = "viewer",
    email: str | None = None,
) -> PortalCalendarMember:
    """Прямое членство в календаре (для тестов RBAC; публичный share API снят)."""
    member = PortalCalendarMember(
        calendar_id=uuid.UUID(str(calendar_id)),
        user_sub=user_sub,
        email=email,
        role=role,
    )
    session.add(member)
    await session.commit()
    await session.refresh(member)
    return member


async def seed_invite_token(
    session: AsyncSession,
    *,
    kind: CalendarInviteKind,
    email: str,
    calendar_id: uuid.UUID | None = None,
    event_id: uuid.UUID | None = None,
    role: str | None = CalendarMemberRole.VIEWER.value,
    expires_at: datetime | None = None,
    used_at: datetime | None = None,
    token: str | None = None,
) -> PortalCalendarInviteToken:
    """Сидировать invite-токен в БД (HTTP create invite нет)."""
    row = PortalCalendarInviteToken(
        token=token or secrets.token_urlsafe(24),
        kind=kind.value,
        calendar_id=calendar_id,
        event_id=event_id,
        email=email.strip().lower(),
        role=role,
        expires_at=expires_at or (now_utc() + timedelta(days=7)),
        used_at=used_at,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row
