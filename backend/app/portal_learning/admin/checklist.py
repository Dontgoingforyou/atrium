from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from app.admin.formatters import fmt_datetime, fmt_user_checklist_status
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_LEARNING
from app.infrastructure.db.models.portal_learning import (
    PortalChecklist,
    PortalChecklistItem,
    PortalUserChecklist,
)
from app.portal_collab.admin.formatters import fmt_user_sub


class PortalChecklistAdmin(ModelView, model=PortalChecklist):
    name = "Чек-лист"
    name_plural = "Чек-листы"
    icon = "fa-solid fa-list-check"
    category = SQLADMIN_CATEGORY_LEARNING

    column_list = [
        PortalChecklist.title,
        PortalChecklist.idp_group,
        PortalChecklist.created_at,
    ]
    column_labels = {
        "title": "Название",
        "description": "Описание",
        "idp_group": "Группа доступа (пусто = для всех)",
        "items": "Пункты шаблона",
        "user_checklists": "Запуски пользователями",
        "created_at": "Создан",
        "updated_at": "Обновлён",
    }
    column_formatters = {
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_details_list = [
        PortalChecklist.title,
        PortalChecklist.description,
        PortalChecklist.idp_group,
        PortalChecklist.created_at,
        PortalChecklist.updated_at,
    ]
    can_view_details = True
    column_searchable_list = [PortalChecklist.title]
    column_sortable_list = [PortalChecklist.title, PortalChecklist.created_at]
    column_default_sort = [(PortalChecklist.created_at, True)]
    form_columns = ["title", "description", "idp_group"]

    async def on_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Request) -> None:
        from app.admin.cas_version import bump_cas_version_on_edit

        bump_cas_version_on_edit(data, model, is_created=is_created)


class PortalChecklistItemAdmin(ModelView, model=PortalChecklistItem):
    name = "Пункт чек-листа"
    name_plural = "Пункты чек-листов"
    icon = "fa-solid fa-check"
    category = SQLADMIN_CATEGORY_LEARNING

    form_ajax_refs = {
        "checklist": {
            "fields": (PortalChecklist.title,),
            "order_by": PortalChecklist.title,
        },
    }

    column_list = [
        "checklist",
        PortalChecklistItem.order_index,
        PortalChecklistItem.text,
    ]
    column_labels = {
        "checklist": "Чек-лист",
        "checklist_id": "Чек-лист (ID)",
        "order_index": "Порядок",
        "text": "Текст пункта",
        "user_item_marks": "Отметки пользователей",
    }
    column_sortable_list = [PortalChecklistItem.order_index]
    form_columns = ["checklist", "order_index", "text"]
    column_details_list = [
        "checklist",
        PortalChecklistItem.order_index,
        PortalChecklistItem.text,
    ]
    can_view_details = True

    def list_query(self, request: Request) -> Any:
        return select(PortalChecklistItem).options(selectinload(PortalChecklistItem.checklist))

    def count_query(self, request: Request) -> Any:
        return select(func.count(PortalChecklistItem.id))

    def details_query(self, request: Request) -> Any:
        return self.form_edit_query(request).options(selectinload(PortalChecklistItem.checklist))


class PortalUserChecklistAdmin(ModelView, model=PortalUserChecklist):
    name = "Прогресс чек-листа"
    name_plural = "Прогресс по чек-листам"
    icon = "fa-solid fa-chart-simple"
    category = SQLADMIN_CATEGORY_LEARNING

    can_create = False
    can_edit = False
    can_delete = True

    column_list = [
        PortalUserChecklist.user_sub,
        "checklist",
        PortalUserChecklist.status,
        PortalUserChecklist.started_at,
        PortalUserChecklist.completed_at,
    ]
    column_labels = {
        "user_sub": "Пользователь",
        "user_profile": "Пользователь (профиль)",
        "checklist": "Чек-лист",
        "checklist_id": "Чек-лист (ID)",
        "status": "Статус",
        "item_marks": "Отметки по пунктам",
        "started_at": "Начат",
        "completed_at": "Завершён",
    }
    column_formatters = {
        "user_sub": fmt_user_sub,  # type: ignore[dict-item, unused-ignore]
        "status": fmt_user_checklist_status,  # type: ignore[dict-item, unused-ignore]
        "started_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "completed_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "user_sub": fmt_user_sub,  # type: ignore[dict-item, unused-ignore]
        "status": fmt_user_checklist_status,  # type: ignore[dict-item, unused-ignore]
        "started_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "completed_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_details_list = [
        PortalUserChecklist.user_sub,
        "checklist",
        PortalUserChecklist.status,
        PortalUserChecklist.started_at,
        PortalUserChecklist.completed_at,
    ]
    can_view_details = True
    column_sortable_list = [PortalUserChecklist.started_at]
    column_default_sort = [(PortalUserChecklist.started_at, True)]

    def list_query(self, request: Request) -> Any:
        return select(PortalUserChecklist).options(
            selectinload(PortalUserChecklist.user_profile),
            selectinload(PortalUserChecklist.checklist),
        )

    def count_query(self, request: Request) -> Any:
        return select(func.count(PortalUserChecklist.id))

    def details_query(self, request: Request) -> Any:
        return self.form_edit_query(request).options(
            selectinload(PortalUserChecklist.user_profile),
            selectinload(PortalUserChecklist.checklist),
        )
