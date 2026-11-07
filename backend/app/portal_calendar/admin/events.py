"""SQLAdmin: события, гости, overrides и напоминания."""

from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms import SelectField
from wtforms.validators import DataRequired, Optional

from app.admin.enum_labels import CALENDAR_REMINDER_CHANNEL_LABELS_RU
from app.admin.formatters import (
    fmt_calendar_reminder_channel,
    fmt_datetime,
)
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_CALENDAR
from app.infrastructure.db.models.portal_calendar import (
    PortalCalendar,
    PortalCalendarAttendee,
    PortalCalendarEvent,
    PortalCalendarEventOverride,
    PortalCalendarReminder,
)
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.admin.formatters import fmt_organizer_sub, fmt_user_sub

_REMINDER_CHANNEL_CHOICES = list(CALENDAR_REMINDER_CHANNEL_LABELS_RU.items())


class PortalCalendarEventAdmin(ModelView, model=PortalCalendarEvent):
    name = "Событие календаря"
    name_plural = "События календаря"
    icon = "fa-solid fa-calendar-check"
    category = SQLADMIN_CATEGORY_CALENDAR

    form_excluded_columns = [
        "organizer_profile",
        "organizer_sub",
        "attendees",
        "overrides",
        "reminders",
        "created_at",
        "updated_at",
        "version",
    ]
    form_ajax_refs = {
        "calendar": {
            "fields": (PortalCalendar.title,),
            "order_by": PortalCalendar.title,
        },
        "organizer_user": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email),
            "order_by": PortalUserProfile.full_name,
        },
    }
    form_args = {
        "calendar": {"validators": [DataRequired()], "label": "Календарь"},
        "organizer_user": {"validators": [DataRequired()], "label": "Организатор"},
    }

    column_list = [
        PortalCalendarEvent.title,
        "calendar",
        PortalCalendarEvent.starts_at,
        PortalCalendarEvent.ends_at,
        PortalCalendarEvent.organizer_sub,
        PortalCalendarEvent.rrule,
    ]
    column_details_list = [
        PortalCalendarEvent.title,
        "calendar",
        PortalCalendarEvent.organizer_sub,
        "organizer_user",
        PortalCalendarEvent.description,
        PortalCalendarEvent.location,
        PortalCalendarEvent.starts_at,
        PortalCalendarEvent.ends_at,
        PortalCalendarEvent.timezone,
        PortalCalendarEvent.rrule,
        PortalCalendarEvent.created_at,
        PortalCalendarEvent.updated_at,
    ]
    column_searchable_list = [
        PortalCalendarEvent.title,
        PortalCalendarEvent.location,
        PortalCalendarEvent.organizer_sub,
    ]
    column_sortable_list = [PortalCalendarEvent.starts_at, PortalCalendarEvent.title, PortalCalendarEvent.updated_at]
    column_default_sort = [(PortalCalendarEvent.starts_at, True)]
    column_formatters = {
        "organizer_sub": fmt_organizer_sub,  # type: ignore[dict-item, unused-ignore]
        "starts_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "ends_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "organizer_sub": fmt_organizer_sub,  # type: ignore[dict-item, unused-ignore]
        "starts_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "ends_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "calendar": "Календарь",
        "calendar_id": "Календарь (ID)",
        "organizer_sub": "Организатор",
        "organizer_user": "Организатор",
        "organizer_profile": "Организатор (профиль)",
        "title": "Заголовок",
        "description": "Описание",
        "location": "Место",
        "starts_at": "Начало",
        "ends_at": "Конец",
        "timezone": "Часовой пояс",
        "rrule": "Повтор (RRULE)",
        "attendees": "Гости",
        "overrides": "Правки вхождений",
        "reminders": "Напоминания",
        "created_at": "Создано",
        "updated_at": "Изменено",
    }
    can_view_details = True

    async def on_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Request) -> None:
        from app.admin.cas_version import bump_cas_version_on_edit

        bump_cas_version_on_edit(data, model, is_created=is_created)
        organizer = data.get("organizer_user")
        if organizer is not None and hasattr(organizer, "sub"):
            data["organizer_sub"] = organizer.sub


class PortalCalendarAttendeeAdmin(ModelView, model=PortalCalendarAttendee):
    name = "Гость события"
    name_plural = "Гости событий"
    icon = "fa-solid fa-envelope-open-text"
    category = SQLADMIN_CATEGORY_CALENDAR

    form_excluded_columns = ["created_at", "status", "responded_at"]
    form_ajax_refs = {
        "event": {
            "fields": (PortalCalendarEvent.title,),
            "order_by": PortalCalendarEvent.starts_at,
        },
    }
    form_args = {
        "event": {"validators": [DataRequired()], "label": "Событие"},
        "user_sub": {"validators": [Optional()], "label": "user_sub"},
        "email": {"validators": [DataRequired()], "label": "Email"},
    }

    column_list = [
        "event",
        PortalCalendarAttendee.email,
        PortalCalendarAttendee.user_sub,
        PortalCalendarAttendee.created_at,
    ]
    column_details_list = [
        "event",
        PortalCalendarAttendee.email,
        PortalCalendarAttendee.user_sub,
        PortalCalendarAttendee.created_at,
    ]
    column_searchable_list = [PortalCalendarAttendee.email, PortalCalendarAttendee.user_sub]
    column_sortable_list = [PortalCalendarAttendee.created_at]
    column_default_sort = [(PortalCalendarAttendee.created_at, True)]
    column_formatters = {
        "user_sub": fmt_user_sub,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "user_sub": fmt_user_sub,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "event": "Событие",
        "event_id": "Событие (ID)",
        "email": "Email",
        "user_sub": "Пользователь",
        "created_at": "Создан",
    }
    can_view_details = True

    def list_query(self, request: Request) -> Any:
        return select(PortalCalendarAttendee).options(
            selectinload(PortalCalendarAttendee.event),
            selectinload(PortalCalendarAttendee.user_profile),
        )

    def details_query(self, request: Request) -> Any:
        return select(PortalCalendarAttendee).options(
            selectinload(PortalCalendarAttendee.event),
            selectinload(PortalCalendarAttendee.user_profile),
        )


class PortalCalendarEventOverrideAdmin(ModelView, model=PortalCalendarEventOverride):
    name = "Правка вхождения"
    name_plural = "Правки вхождений"
    icon = "fa-solid fa-calendar-xmark"
    category = SQLADMIN_CATEGORY_CALENDAR

    form_ajax_refs = {
        "event": {
            "fields": (PortalCalendarEvent.title,),
            "order_by": PortalCalendarEvent.starts_at,
        },
    }
    form_args = {
        "event": {"validators": [DataRequired()], "label": "Событие"},
    }

    column_list = [
        "event",
        PortalCalendarEventOverride.original_start,
        PortalCalendarEventOverride.title,
        PortalCalendarEventOverride.is_cancelled,
        PortalCalendarEventOverride.starts_at,
    ]
    column_details_list = [
        "event",
        PortalCalendarEventOverride.original_start,
        PortalCalendarEventOverride.starts_at,
        PortalCalendarEventOverride.ends_at,
        PortalCalendarEventOverride.title,
        PortalCalendarEventOverride.description,
        PortalCalendarEventOverride.location,
        PortalCalendarEventOverride.is_cancelled,
    ]
    column_searchable_list = [PortalCalendarEventOverride.title]
    column_sortable_list = [PortalCalendarEventOverride.original_start]
    column_default_sort = [(PortalCalendarEventOverride.original_start, True)]
    column_formatters = {
        "original_start": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "starts_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "ends_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "original_start": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "starts_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "ends_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "event": "Событие",
        "event_id": "Событие (ID)",
        "original_start": "Оригинальное начало",
        "starts_at": "Новое начало",
        "ends_at": "Новый конец",
        "title": "Заголовок",
        "description": "Описание",
        "location": "Место",
        "is_cancelled": "Отменено",
    }
    can_view_details = True


class PortalCalendarReminderAdmin(ModelView, model=PortalCalendarReminder):
    name = "Напоминание"
    name_plural = "Напоминания"
    icon = "fa-solid fa-bell"
    category = SQLADMIN_CATEGORY_CALENDAR

    form_overrides = {"channel": SelectField}
    form_ajax_refs = {
        "event": {
            "fields": (PortalCalendarEvent.title,),
            "order_by": PortalCalendarEvent.starts_at,
        },
    }
    form_args = {
        "event": {"validators": [DataRequired()], "label": "Событие"},
        "channel": {"label": "Канал", "choices": _REMINDER_CHANNEL_CHOICES},
    }
    form_widget_args = {
        "offset_minutes": {"min": 0, "placeholder": "напр. 15"},
    }

    column_list = [
        "event",
        PortalCalendarReminder.offset_minutes,
        PortalCalendarReminder.channel,
    ]
    column_details_list = [
        "event",
        PortalCalendarReminder.offset_minutes,
        PortalCalendarReminder.channel,
    ]
    column_sortable_list = [PortalCalendarReminder.offset_minutes, PortalCalendarReminder.channel]
    column_formatters = {
        "channel": fmt_calendar_reminder_channel,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "channel": fmt_calendar_reminder_channel,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "event": "Событие",
        "event_id": "Событие (ID)",
        "offset_minutes": "За сколько минут",
        "channel": "Канал",
    }
    can_view_details = True
