from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from wtforms.validators import DataRequired

from app.admin.formatters import fmt_datetime
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_TASKS
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_time_entry import PortalTimeEntry
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.admin.formatters import fmt_user_sub


class PortalTimeEntryAdmin(ModelView, model=PortalTimeEntry):
    name = "Запись таймшита"
    name_plural = "Таймшиты"
    icon = "fa-solid fa-hourglass-half"
    category = SQLADMIN_CATEGORY_TASKS

    form_excluded_columns = ["user_profile", "user_sub", "created_at", "updated_at", "version"]
    form_ajax_refs = {
        "task": {
            "fields": (PortalTask.title,),
            "order_by": PortalTask.created_at,
        },
        "user_user": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email),
            "order_by": PortalUserProfile.full_name,
        },
    }
    form_args = {
        "user_user": {"validators": [DataRequired()], "label": "Пользователь"},
    }

    column_list = [
        PortalTimeEntry.user_sub,
        PortalTimeEntry.worked_on,
        PortalTimeEntry.minutes,
        PortalTimeEntry.task_name,
        "task",
        PortalTimeEntry.created_at,
    ]
    column_details_list = [
        PortalTimeEntry.user_sub,
        PortalTimeEntry.worked_on,
        PortalTimeEntry.minutes,
        "task",
        PortalTimeEntry.task_name,
        PortalTimeEntry.note,
        PortalTimeEntry.created_at,
        PortalTimeEntry.updated_at,
    ]
    column_formatters = {
        "user_sub": fmt_user_sub,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "user_sub": fmt_user_sub,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_default_sort = [(PortalTimeEntry.worked_on, True)]
    column_labels = {
        "id": "Внутренний номер",
        "user_sub": "Пользователь",
        "user_user": "Пользователь",
        "worked_on": "Дата работы",
        "minutes": "Продолжительность (мин.)",
        "task_id": "Задача (идентификатор)",
        "task": "Задача",
        "task_name": "Название задачи",
        "note": "Комментарий",
        "created_at": "Создано",
        "updated_at": "Изменено",
    }
    form_widget_args = {
        "minutes": {"min": 1, "max": 1440, "placeholder": "напр. 60"},
    }
    can_view_details = True

    async def on_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Any) -> None:
        from app.admin.cas_version import bump_cas_version_on_edit

        bump_cas_version_on_edit(data, model, is_created=is_created)
        user_user = data.get("user_user")
        if user_user is not None and hasattr(user_user, "sub"):
            data["user_sub"] = user_user.sub
        if model is not None:
            model.updated_at = now_utc()
