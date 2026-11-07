"""Список календарей на экране — только свои; показ другим отделам — только админ."""

from __future__ import annotations

from app.core.auth_constants import SSO_GID_OUTSTAFF
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.schemas.auth import UserPublic
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.helpers.portal_test_users import user_portal_admin
from tests.portal_calendar.conftest import (
    CALENDAR_API,
    as_user,
    as_user_b,
    assert_api_error,
    ensure_primary,
    seed_calendar_member,
)

SHARED = f"{CALENDAR_API}/calendars/shared"


def _admin() -> UserPublic:
    return user_portal_admin().model_copy(update={"gid_number": SSO_GID_OUTSTAFF})


async def test_list_hides_calendar_where_user_is_only_a_member(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    with as_user_b():
        foreign = await ensure_primary(client_user)
    await seed_calendar_member(sqlite_session, foreign["id"], "user-sub", role="viewer")

    own = await ensure_primary(client_user)
    listed = await client_user.get(f"{CALENDAR_API}/calendars")

    assert listed.status_code == 200, listed.text
    ids = [item["id"] for item in listed.json()]
    assert own["id"] in ids
    assert foreign["id"] not in ids
    assert all(item["owner_sub"] == "user-sub" for item in listed.json())


async def test_manager_cannot_show_calendar_to_other_departments(client_user: AsyncClient) -> None:
    primary = await ensure_primary(client_user)
    response = await client_user.patch(
        f"{CALENDAR_API}/calendars/{primary['id']}/show",
        json={"enabled": True},
    )
    assert_api_error(response, 403, "forbidden")


async def test_manager_cannot_list_calendars_shared_to_departments(client_user: AsyncClient) -> None:
    response = await client_user.get(SHARED)
    assert_api_error(response, 403, "forbidden")


async def test_admin_lists_only_calendars_with_show_flag_and_department(
    client_user: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    profile = await sqlite_session.get(PortalUserProfile, "admin-sub")
    assert profile is not None
    profile.gid_number = SSO_GID_OUTSTAFF
    await sqlite_session.commit()

    with as_user(_admin):
        primary = await ensure_primary(client_user)
        created = await client_user.post(
            f"{CALENDAR_API}/calendars",
            json={"title": "Скрытый", "color": "#112233"},
        )
        assert created.status_code == 201, created.text
        shown = await client_user.patch(
            f"{CALENDAR_API}/calendars/{primary['id']}/show",
            json={"enabled": True},
        )
        assert shown.status_code == 200, shown.text
        listed = await client_user.get(SHARED)

    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert [item["id"] for item in body] == [primary["id"]]
    assert body[0]["show_to_other_departments"] is True
    assert body[0]["department_id"] == SSO_GID_OUTSTAFF
    assert body[0]["department_label"] == "Аутстафф"
    assert body[0]["owner_label"] == "Admin"
