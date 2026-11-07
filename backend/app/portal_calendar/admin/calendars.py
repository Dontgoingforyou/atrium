"""SQLAdmin: календари и участники шаринга."""

from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms import SelectField
from wtforms.validators import DataRequired, Optional

from app.admin.enum_labels import CALENDAR_MEMBER_ROLE_LABELS_RU
from app.admin.formatters import fmt_calendar_member_role, fmt_color, fmt_datetime
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_CALENDAR
from app.admin.views.documents import ColorPickerWidget
from app.infrastructure.db.models.portal_calendar import PortalCalendar, PortalCalendarMember
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.admin.formatters import fmt_owner_sub, fmt_user_sub

_MEMBER_ROLE_CHOICES = list(CALENDAR_MEMBER_ROLE_LABELS_RU.items())


class PortalCalendarAdmin(ModelView, model=PortalCalendar):
    name = "Календарь"
    name_plural = "Календари"
    icon = "fa-solid fa-calendar-days"
    category = SQLADMIN_CATEGORY_CALENDAR
    category_icon = "fa-solid fa-calendar"

    form_excluded_columns = [
        "owner_profile",
        "owner_sub",
        "members",
        "events",
        "created_at",
        "updated_at",
    ]
    form_ajax_refs = {
        "owner_user": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email),
            "order_by": PortalUserProfile.full_name,
        },
    }
    form_args = {
        "owner_user": {"validators": [DataRequired()], "label": "Владелец"},
        "color": {"widget": ColorPickerWidget(), "label": "Цвет"},
    }

    column_list = [
        PortalCalendar.title,
        PortalCalendar.owner_sub,
        PortalCalendar.color,
        PortalCalendar.is_primary,
        PortalCalendar.timezone,
        PortalCalendar.updated_at,
    ]
    column_details_list = [
        PortalCalendar.title,
        PortalCalendar.owner_sub,
        "owner_user",
        PortalCalendar.color,
        PortalCalendar.timezone,
        PortalCalendar.is_primary,
        PortalCalendar.created_at,
        PortalCalendar.updated_at,
    ]
    column_searchable_list = [PortalCalendar.title, PortalCalendar.owner_sub]
    column_sortable_list = [PortalCalendar.title, PortalCalendar.updated_at, PortalCalendar.is_primary]
    column_default_sort = [(PortalCalendar.updated_at, True)]
    column_formatters = {
        "owner_sub": fmt_owner_sub,  # type: ignore[dict-item, unused-ignore]
        "color": fmt_color,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "owner_sub": fmt_owner_sub,  # type: ignore[dict-item, unused-ignore]
        "color": fmt_color,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "title": "Название",
        "owner_sub": "Владелец",
        "owner_user": "Владелец",
        "owner_profile": "Владелец (профиль)",
        "color": "Цвет",
        "timezone": "Часовой пояс",
        "is_primary": "Основной",
        "members": "Участники",
        "events": "События",
        "created_at": "Создан",
        "updated_at": "Изменён",
    }
    can_view_details = True

    async def on_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Request) -> None:
        owner = data.get("owner_user")
        if owner is not None and hasattr(owner, "sub"):
            data["owner_sub"] = owner.sub


class PortalCalendarMemberAdmin(ModelView, model=PortalCalendarMember):
    name = "Участник календаря"
    name_plural = "Участники календарей"
    icon = "fa-solid fa-user-group"
    category = SQLADMIN_CATEGORY_CALENDAR

    form_excluded_columns = ["created_at"]
    form_overrides = {"role": SelectField}
    form_ajax_refs = {
        "calendar": {
            "fields": (PortalCalendar.title,),
            "order_by": PortalCalendar.title,
        },
    }
    form_args = {
        "calendar": {"validators": [DataRequired()], "label": "Календарь"},
        "role": {"label": "Роль", "choices": _MEMBER_ROLE_CHOICES},
        "user_sub": {"validators": [Optional()], "label": "user_sub"},
        "email": {"validators": [Optional()], "label": "Email"},
    }

    column_list = [
        "calendar",
        PortalCalendarMember.user_sub,
        PortalCalendarMember.email,
        PortalCalendarMember.role,
        PortalCalendarMember.created_at,
    ]
    column_details_list = [
        "calendar",
        PortalCalendarMember.user_sub,
        PortalCalendarMember.email,
        PortalCalendarMember.role,
        PortalCalendarMember.created_at,
    ]
    column_searchable_list = [PortalCalendarMember.user_sub, PortalCalendarMember.email]
    column_sortable_list = [PortalCalendarMember.created_at, PortalCalendarMember.role]
    column_default_sort = [(PortalCalendarMember.created_at, True)]
    column_formatters = {
        "user_sub": fmt_user_sub,  # type: ignore[dict-item, unused-ignore]
        "role": fmt_calendar_member_role,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "user_sub": fmt_user_sub,  # type: ignore[dict-item, unused-ignore]
        "role": fmt_calendar_member_role,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "calendar": "Календарь",
        "calendar_id": "Календарь (ID)",
        "user_sub": "Пользователь",
        "email": "Email",
        "role": "Роль",
        "created_at": "Создан",
    }
    can_view_details = True

    def list_query(self, request: Request) -> Any:
        return select(PortalCalendarMember).options(
            selectinload(PortalCalendarMember.calendar),
            selectinload(PortalCalendarMember.user_profile),
        )

    def details_query(self, request: Request) -> Any:
        return select(PortalCalendarMember).options(
            selectinload(PortalCalendarMember.calendar),
            selectinload(PortalCalendarMember.user_profile),
        )
