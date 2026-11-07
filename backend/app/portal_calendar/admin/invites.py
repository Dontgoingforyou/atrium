"""SQLAdmin: invite-токены и журнал отправленных напоминаний."""

from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms import SelectField
from wtforms.validators import DataRequired, Optional

from app.admin.enum_labels import CALENDAR_INVITE_KIND_LABELS_RU, CALENDAR_MEMBER_ROLE_LABELS_RU
from app.admin.formatters import (
    fmt_calendar_invite_kind,
    fmt_calendar_member_role,
    fmt_datetime,
)
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_CALENDAR
from app.infrastructure.db.models.portal_calendar import (
    PortalCalendar,
    PortalCalendarEvent,
    PortalCalendarInviteToken,
    PortalCalendarReminder,
    PortalCalendarReminderSent,
)
from app.portal_collab.admin.formatters import fmt_calendar_reminder_recipient

_INVITE_KIND_CHOICES = list(CALENDAR_INVITE_KIND_LABELS_RU.items())
_MEMBER_ROLE_CHOICES = list(CALENDAR_MEMBER_ROLE_LABELS_RU.items())


class PortalCalendarInviteTokenAdmin(ModelView, model=PortalCalendarInviteToken):
    name = "Invite-токен"
    name_plural = "Invite-токены"
    icon = "fa-solid fa-link"
    category = SQLADMIN_CATEGORY_CALENDAR

    form_excluded_columns = ["created_at"]
    form_overrides = {
        "kind": SelectField,
        "role": SelectField,
    }
    form_ajax_refs = {
        "calendar": {
            "fields": (PortalCalendar.title,),
            "order_by": PortalCalendar.title,
        },
        "event": {
            "fields": (PortalCalendarEvent.title,),
            "order_by": PortalCalendarEvent.starts_at,
        },
    }
    form_args = {
        "kind": {"label": "Тип", "choices": _INVITE_KIND_CHOICES},
        "role": {
            "label": "Роль (для шаринга)",
            "choices": [("", "—")] + _MEMBER_ROLE_CHOICES,
            "validators": [Optional()],
        },
        "email": {"validators": [DataRequired()], "label": "Email"},
        "token": {"validators": [DataRequired()], "label": "Токен"},
        "calendar": {"validators": [Optional()], "label": "Календарь"},
        "event": {"validators": [Optional()], "label": "Событие"},
    }

    column_list = [
        PortalCalendarInviteToken.kind,
        PortalCalendarInviteToken.email,
        "calendar",
        "event",
        PortalCalendarInviteToken.expires_at,
        PortalCalendarInviteToken.used_at,
    ]
    column_details_list = [
        PortalCalendarInviteToken.token,
        PortalCalendarInviteToken.kind,
        PortalCalendarInviteToken.email,
        PortalCalendarInviteToken.role,
        "calendar",
        "event",
        PortalCalendarInviteToken.expires_at,
        PortalCalendarInviteToken.used_at,
        PortalCalendarInviteToken.created_at,
    ]
    column_searchable_list = [PortalCalendarInviteToken.email]
    column_sortable_list = [
        PortalCalendarInviteToken.created_at,
        PortalCalendarInviteToken.expires_at,
        PortalCalendarInviteToken.kind,
    ]
    column_default_sort = [(PortalCalendarInviteToken.created_at, True)]
    column_formatters = {
        "kind": fmt_calendar_invite_kind,  # type: ignore[dict-item, unused-ignore]
        "role": fmt_calendar_member_role,  # type: ignore[dict-item, unused-ignore]
        "expires_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "used_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "kind": fmt_calendar_invite_kind,  # type: ignore[dict-item, unused-ignore]
        "role": fmt_calendar_member_role,  # type: ignore[dict-item, unused-ignore]
        "expires_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "used_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "token": "Токен",
        "kind": "Тип",
        "email": "Email",
        "role": "Роль",
        "calendar": "Календарь",
        "calendar_id": "Календарь (ID)",
        "event": "Событие",
        "event_id": "Событие (ID)",
        "expires_at": "Истекает",
        "used_at": "Использован",
        "created_at": "Создан",
    }
    can_view_details = True


class PortalCalendarReminderSentAdmin(ModelView, model=PortalCalendarReminderSent):
    """Журнал идемпотентности — обычно только просмотр/очистка."""

    name = "Отправленное напоминание"
    name_plural = "Отправленные напоминания"
    icon = "fa-solid fa-paper-plane"
    category = SQLADMIN_CATEGORY_CALENDAR

    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True

    form_ajax_refs = {
        "reminder": {
            "fields": (PortalCalendarReminder.channel,),
            "order_by": PortalCalendarReminder.offset_minutes,
        },
    }

    column_list = [
        "reminder",
        PortalCalendarReminderSent.occurrence_start,
        PortalCalendarReminderSent.recipient_key,
        PortalCalendarReminderSent.sent_at,
    ]
    column_details_list = [
        "reminder",
        PortalCalendarReminderSent.occurrence_start,
        PortalCalendarReminderSent.recipient_key,
        PortalCalendarReminderSent.sent_at,
    ]
    column_searchable_list = [PortalCalendarReminderSent.recipient_key]
    column_sortable_list = [PortalCalendarReminderSent.sent_at, PortalCalendarReminderSent.occurrence_start]
    column_default_sort = [(PortalCalendarReminderSent.sent_at, True)]
    column_formatters = {
        "recipient_key": fmt_calendar_reminder_recipient,  # type: ignore[dict-item, unused-ignore]
        "occurrence_start": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "sent_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "recipient_key": fmt_calendar_reminder_recipient,  # type: ignore[dict-item, unused-ignore]
        "occurrence_start": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "sent_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "reminder": "Напоминание",
        "reminder_id": "Напоминание (ID)",
        "occurrence_start": "Вхождение",
        "recipient_key": "Получатель",
        "sent_at": "Отправлено",
    }

    def list_query(self, request: Request) -> Any:
        return select(PortalCalendarReminderSent).options(
            selectinload(PortalCalendarReminderSent.reminder),
            selectinload(PortalCalendarReminderSent.recipient_profile),
        )

    def details_query(self, request: Request) -> Any:
        return select(PortalCalendarReminderSent).options(
            selectinload(PortalCalendarReminderSent.reminder),
            selectinload(PortalCalendarReminderSent.recipient_profile),
        )
