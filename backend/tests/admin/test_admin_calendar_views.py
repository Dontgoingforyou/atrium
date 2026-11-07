"""Контракт SQLAdmin-вьюх календаря: хуки, can_*, форматтеры."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_CALENDAR
from app.infrastructure.db.models.portal_calendar import PortalCalendarInviteToken
from app.portal_calendar.admin import (
    PortalCalendarAdmin,
    PortalCalendarAttendeeAdmin,
    PortalCalendarEventAdmin,
    PortalCalendarEventOverrideAdmin,
    PortalCalendarInviteTokenAdmin,
    PortalCalendarMemberAdmin,
    PortalCalendarReminderAdmin,
    PortalCalendarReminderSentAdmin,
)
from app.portal_collab.admin.formatters import (
    fmt_calendar_reminder_recipient,
    fmt_organizer_sub,
    fmt_owner_sub,
)
from starlette.requests import Request


def test_calendar_admin_category_and_crud_flags() -> None:
    views = [
        PortalCalendarAdmin,
        PortalCalendarMemberAdmin,
        PortalCalendarEventAdmin,
        PortalCalendarAttendeeAdmin,
        PortalCalendarEventOverrideAdmin,
        PortalCalendarReminderAdmin,
        PortalCalendarInviteTokenAdmin,
        PortalCalendarReminderSentAdmin,
    ]
    assert all(v.category == SQLADMIN_CATEGORY_CALENDAR for v in views)

    assert PortalCalendarReminderSentAdmin.can_create is False
    assert PortalCalendarReminderSentAdmin.can_edit is False
    assert PortalCalendarReminderSentAdmin.can_delete is True

    # Invite-токен намеренно редактируемый (в т.ч. поле token в details) — god-mode portal_admin.
    assert PortalCalendarInviteTokenAdmin.can_create is True
    assert PortalCalendarInviteTokenAdmin.can_edit is True
    assert PortalCalendarInviteToken.token in PortalCalendarInviteTokenAdmin.column_details_list

    excluded = PortalCalendarAttendeeAdmin.form_excluded_columns
    assert "status" in excluded
    assert "responded_at" in excluded


@pytest.mark.asyncio
async def test_calendar_admin_on_model_change_sets_owner_sub() -> None:
    admin = PortalCalendarAdmin()
    req = Request({"type": "http", "method": "POST", "path": "/admin/portal-calendar/create"})
    data: dict = {"owner_user": SimpleNamespace(sub="owner-1")}
    await admin.on_model_change(data, None, True, req)
    assert data["owner_sub"] == "owner-1"


@pytest.mark.asyncio
async def test_calendar_admin_on_model_change_skips_owner_without_sub() -> None:
    admin = PortalCalendarAdmin()
    req = Request({"type": "http", "method": "POST", "path": "/admin/portal-calendar/edit"})
    data: dict = {"owner_user": SimpleNamespace(full_name="Анна"), "owner_sub": "kept"}
    await admin.on_model_change(data, None, False, req)
    assert data["owner_sub"] == "kept"


@pytest.mark.asyncio
async def test_calendar_event_admin_on_model_change_sets_organizer_sub() -> None:
    admin = PortalCalendarEventAdmin()
    req = Request({"type": "http", "method": "POST", "path": "/admin/portal-calendar-event/create"})
    data: dict = {"organizer_user": SimpleNamespace(sub="org-1")}
    await admin.on_model_change(data, None, True, req)
    assert data["organizer_sub"] == "org-1"


@pytest.mark.asyncio
async def test_calendar_event_admin_on_model_change_skips_missing_organizer() -> None:
    admin = PortalCalendarEventAdmin()
    req = Request({"type": "http", "method": "POST", "path": "/admin/portal-calendar-event/edit"})
    data: dict = {"organizer_sub": "kept-org"}
    await admin.on_model_change(data, None, False, req)
    assert data["organizer_sub"] == "kept-org"


def test_owner_organizer_formatters() -> None:
    assert (
        fmt_owner_sub(
            SimpleNamespace(owner_profile=SimpleNamespace(full_name="Анна", email="a@t"), owner_sub="s1"),
            "owner_sub",
        )
        == "Анна (a@t)"
    )
    assert (
        fmt_organizer_sub(
            SimpleNamespace(organizer_profile=None, organizer_sub="org-sub"),
            "organizer_sub",
        )
        == "org-sub"
    )


def test_calendar_reminder_recipient_formatter() -> None:
    assert (
        fmt_calendar_reminder_recipient(
            SimpleNamespace(
                recipient_key="sub:abc",
                recipient_profile=SimpleNamespace(full_name="Иван", email="i@t"),
            ),
            "recipient_key",
        )
        == "Иван (i@t)"
    )
    assert (
        fmt_calendar_reminder_recipient(
            SimpleNamespace(recipient_key="email:mishael000@yandex.ru", recipient_profile=None),
            "recipient_key",
        )
        == "mishael000@yandex.ru"
    )
    assert (
        fmt_calendar_reminder_recipient(
            SimpleNamespace(recipient_key="sub:orphan-sub", recipient_profile=None),
            "recipient_key",
        )
        == "orphan-sub"
    )
    assert fmt_calendar_reminder_recipient(SimpleNamespace(recipient_key=""), "recipient_key") == "—"
    assert fmt_calendar_reminder_recipient(SimpleNamespace(recipient_key="email:"), "recipient_key") == "—"
