"""Пакет admin-представлений для portal_calendar."""

from app.portal_calendar.admin.calendars import PortalCalendarAdmin, PortalCalendarMemberAdmin
from app.portal_calendar.admin.events import (
    PortalCalendarAttendeeAdmin,
    PortalCalendarEventAdmin,
    PortalCalendarEventOverrideAdmin,
    PortalCalendarReminderAdmin,
)
from app.portal_calendar.admin.invites import PortalCalendarInviteTokenAdmin, PortalCalendarReminderSentAdmin

__all__ = [
    "PortalCalendarAdmin",
    "PortalCalendarMemberAdmin",
    "PortalCalendarEventAdmin",
    "PortalCalendarAttendeeAdmin",
    "PortalCalendarEventOverrideAdmin",
    "PortalCalendarReminderAdmin",
    "PortalCalendarInviteTokenAdmin",
    "PortalCalendarReminderSentAdmin",
]
