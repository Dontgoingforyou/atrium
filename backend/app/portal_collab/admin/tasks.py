from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from sqladmin.ajax import QueryAjaxModelLoader
from sqlalchemy import Select, String, cast, or_, select
from sqlalchemy.orm import selectinload, undefer
from starlette.requests import Request
from wtforms import SelectField
from wtforms.validators import DataRequired, Optional

from app.admin.enum_labels import TASK_STATUS_LABELS_RU
from app.admin.formatters import fmt_color, fmt_datetime, fmt_diff, fmt_task_priority, fmt_task_status
from app.admin.model_converter import CosmoletAdminModelConverter
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_TASKS
from app.admin.views.documents import ColorPickerWidget
from app.infrastructure.db.models.portal_chat import PortalChat
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskColumn, PortalTaskComment, PortalTaskHistory
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.admin.formatters import (
    fmt_assignee_sub,
    fmt_author_sub,
    fmt_changed_by,
    fmt_creator_sub,
    fmt_mentioned_names,
)

# PortalTask.status хранится как обычный String (не SQLAlchemy Enum) — CosmoletAdminModelConverter
# на такие колонки не срабатывает, поэтому подписи для формы берём из общего enum_labels вручную.
# PortalTask.priority — настоящий SQLAlchemy Enum, его форму строит конвертер (form_converter ниже).
_TASK_STATUS_CHOICES = list(TASK_STATUS_LABELS_RU.items())


class _TaskLinkChatLoader(QueryAjaxModelLoader):
    """Чаты, привязываемые к задаче: любой чат портала."""

    async def get_list(self, *args: Any, **kwargs: Any) -> list[Any]:  # type: ignore[override, unused-ignore]
        term = str(kwargs["term"] if "term" in kwargs else args[-1])
        stmt = select(PortalChat)
        filters = [cast(field, String).ilike(f"%%{term}%%") for field in self._cached_fields]
        stmt = stmt.filter(or_(*filters))
        if self.order_by:
            order_exprs = self.order_by if isinstance(self.order_by, list) else [self.order_by]
            for order_expr in order_exprs:
                stmt = stmt.order_by(order_expr)
        stmt = stmt.limit(self.limit)
        return await self.model_admin._run_query(stmt)  # type: ignore[no-any-return]


class PortalTaskAdmin(ModelView, model=PortalTask):
    name = "Задача портала"
    name_plural = "Задачи портала"
    icon = "fa-solid fa-list-check"
    category = SQLADMIN_CATEGORY_TASKS
    category_icon = "fa-solid fa-clipboard-list"

    form_converter = CosmoletAdminModelConverter
    form_excluded_columns = [
        "creator_profile",
        "assignee_profile",
        "creator_sub",
        "assignee_sub",
        "history",
        "comments",
        "subtasks",
        "parent_task",
        "created_at",
        "updated_at",
        "version",
    ]
    # priority — не здесь: SelectField для него строит CosmoletAdminModelConverter (это Enum-столбец)
    form_overrides = {
        "status": SelectField,
    }
    form_ajax_refs = {
        "creator_user": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email),
            "order_by": PortalUserProfile.full_name,
        },
        "assignee_user": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email),
            "order_by": PortalUserProfile.full_name,
        },
        "parent_task": {
            "fields": (PortalTask.title,),
            "order_by": PortalTask.title,
        },
    }
    form_args = {
        "creator_user": {"validators": [DataRequired()], "label": "Создатель"},
        "assignee_user": {"validators": [Optional()], "label": "Исполнитель"},
        "parent_task": {"validators": [Optional()], "label": "Родительская задача"},
        "status": {"label": "Статус", "choices": _TASK_STATUS_CHOICES},
    }

    def __init__(self) -> None:
        super().__init__()
        self._form_ajax_refs["chat"] = _TaskLinkChatLoader(
            "chat",
            PortalChat,
            self,
            fields=(PortalChat.title,),
            order_by=PortalChat.title,
        )

    async def on_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Request) -> None:
        """Синхронизировать creator_sub/assignee_sub из выбранных creator_user/assignee_user.

        ``creator_sub``/``assignee_sub`` исключены из формы (``form_excluded_columns``), поэтому
        без этого шага они не проставляются при создании/правке задачи через ``/admin`` — по
        образцу ``PortalAgreementAdmin.on_model_change`` (``created_by_sub`` из ``created_by_user``).
        """
        from app.admin.cas_version import bump_cas_version_on_edit

        bump_cas_version_on_edit(data, model, is_created=is_created)
        cu = data.get("creator_user")
        if cu is not None and hasattr(cu, "sub"):
            data["creator_sub"] = cu.sub
        au = data.get("assignee_user")
        data["assignee_sub"] = au.sub if au is not None and hasattr(au, "sub") else None

    column_list = [
        PortalTask.title,
        PortalTask.status,
        PortalTask.creator_sub,
        PortalTask.assignee_sub,
        PortalTask.created_at,
    ]
    column_details_list = [
        PortalTask.title,
        PortalTask.description,
        PortalTask.status,
        PortalTask.priority,
        PortalTask.creator_sub,
        PortalTask.assignee_sub,
        PortalTask.due_at,
        "parent_task",
        "document",
        "chat",
        PortalTask.created_at,
        PortalTask.updated_at,
    ]
    column_formatters = {
        "creator_sub": fmt_creator_sub,  # type: ignore[dict-item, unused-ignore]
        "assignee_sub": fmt_assignee_sub,  # type: ignore[dict-item, unused-ignore]
        "status": fmt_task_status,  # type: ignore[dict-item, unused-ignore]
        "priority": fmt_task_priority,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "due_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "creator_sub": fmt_creator_sub,  # type: ignore[dict-item, unused-ignore]
        "assignee_sub": fmt_assignee_sub,  # type: ignore[dict-item, unused-ignore]
        "status": fmt_task_status,  # type: ignore[dict-item, unused-ignore]
        "priority": fmt_task_priority,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "due_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_default_sort = [(PortalTask.created_at, True)]
    column_labels = {
        "id": "Внутренний номер",
        "title": "Заголовок",
        "description": "Описание",
        "creator_sub": "Создатель",
        "assignee_sub": "Исполнитель",
        "creator_user": "Создатель",
        "assignee_user": "Исполнитель",
        "status": "Статус",
        "priority": "Приоритет",
        "due_at": "Срок",
        "document_id": "Документ (идентификатор)",
        "source_message_id": "Исходное сообщение (идентификатор)",
        "chat_id": "Чат (идентификатор)",
        "parent_task_id": "Родительская задача (идентификатор)",
        "parent_task": "Родительская задача",
        "subtasks": "Подзадачи",
        "comments": "Комментарии",
        "created_at": "Создана",
        "updated_at": "Изменена",
        "document": "Документ",
        "source_message": "Исходное сообщение",
        "chat": "Чат",
        "history": "История",
    }
    can_view_details = True


class PortalTaskHistoryAdmin(ModelView, model=PortalTaskHistory):
    name = "История задачи"
    name_plural = "История задач"
    icon = "fa-solid fa-clock-rotate-left"
    category = SQLADMIN_CATEGORY_TASKS

    can_create = False
    can_edit = False
    form_excluded_columns = ["changed_by_profile"]

    column_list = ["task", PortalTaskHistory.changed_by_sub, PortalTaskHistory.changed_at]
    column_details_list = [
        "task",
        PortalTaskHistory.changed_by_sub,
        PortalTaskHistory.changed_at,
        PortalTaskHistory.diff,
    ]
    column_formatters = {
        "changed_by_sub": fmt_changed_by,  # type: ignore[dict-item, unused-ignore]
        "changed_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "changed_by_sub": fmt_changed_by,  # type: ignore[dict-item, unused-ignore]
        "changed_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "diff": fmt_diff,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "task_id": "Задача (идентификатор)",
        "task": "Задача",
        "changed_by_sub": "Кто изменил",
        "changed_at": "Время изменения",
        "diff": "Что изменилось",
    }
    can_view_details = True


class PortalTaskCommentAdmin(ModelView, model=PortalTaskComment):
    name = "Комментарий задачи"
    name_plural = "Комментарии задач"
    icon = "fa-solid fa-comment"
    category = SQLADMIN_CATEGORY_TASKS

    can_create = False

    form_excluded_columns = [
        "author_sub",
        "author_profile",
        "replies",
        "parent",
        "mentions",
        "mentioned_names",
        "created_at",
        "updated_at",
        "version",
    ]
    form_ajax_refs = {
        "author_user": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email),
            "order_by": PortalUserProfile.full_name,
        },
    }
    form_args = {
        "author_user": {"validators": [DataRequired()], "label": "Автор"},
    }

    column_list = [
        "task",
        PortalTaskComment.author_sub,
        PortalTaskComment.body,
        PortalTaskComment.created_at,
    ]
    column_details_list = [
        "task",
        "parent",
        PortalTaskComment.author_sub,
        PortalTaskComment.body,
        "mentioned_names",
        PortalTaskComment.created_at,
        PortalTaskComment.updated_at,
    ]
    column_formatters = {
        "author_sub": fmt_author_sub,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "author_sub": fmt_author_sub,  # type: ignore[dict-item, unused-ignore]
        "mentioned_names": fmt_mentioned_names,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_default_sort = [(PortalTaskComment.created_at, True)]
    column_labels = {
        "id": "Внутренний номер",
        "task_id": "Задача (идентификатор)",
        "task": "Задача",
        "parent_id": "Родительский комментарий (идентификатор)",
        "parent": "Родительский комментарий",
        "author_sub": "Автор",
        "author_user": "Автор",
        "body": "Текст",
        "mentions": "Упоминания (raw)",
        "mentioned_names": "Упоминания",
        "created_at": "Создан",
        "updated_at": "Изменён",
    }
    can_view_details = True

    async def on_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Request) -> None:
        """Синхронизировать author_sub из ajax-пикера author_user (поле исключено из формы)."""
        from app.admin.cas_version import bump_cas_version_on_edit

        bump_cas_version_on_edit(data, model, is_created=is_created)
        au = data.get("author_user")
        if au is not None and hasattr(au, "sub"):
            data["author_sub"] = au.sub

    def details_query(self, request: Request) -> Select[Any]:
        return select(PortalTaskComment).options(
            selectinload(PortalTaskComment.parent),
            undefer(PortalTaskComment.mentioned_names),  # type: ignore[attr-defined]
        )


def _fmt_status_key(model: Any, attr: str) -> str:
    val = str(getattr(model, attr, "") or "")
    label = TASK_STATUS_LABELS_RU.get(val, val)
    return f"{label} ({val})" if label != val else val


class PortalTaskColumnAdmin(ModelView, model=PortalTaskColumn):
    name = "Колонка канбана"
    name_plural = "Колонки канбана"
    icon = "fa-solid fa-table-columns"
    category = SQLADMIN_CATEGORY_TASKS

    column_list = [
        PortalTaskColumn.position,
        PortalTaskColumn.title,
        PortalTaskColumn.status_key,
        PortalTaskColumn.jira_status_id,
        PortalTaskColumn.color,
        PortalTaskColumn.exclude_from_kpi,
    ]
    column_details_list = [
        PortalTaskColumn.position,
        PortalTaskColumn.title,
        PortalTaskColumn.status_key,
        PortalTaskColumn.jira_status_id,
        PortalTaskColumn.color,
        PortalTaskColumn.exclude_from_kpi,
        PortalTaskColumn.id,
    ]
    column_default_sort = [(PortalTaskColumn.position, False)]
    column_sortable_list = [PortalTaskColumn.position, PortalTaskColumn.title]
    column_labels = {
        "id": "Идентификатор",
        "title": "Заголовок",
        "status_key": "Статус",
        "jira_status_id": "ID статуса Jira (AUTASKS)",
        "color": "Цвет",
        "position": "Порядок",
        "exclude_from_kpi": "Исключить из KPI",
    }
    column_formatters = {
        "color": fmt_color,  # type: ignore[dict-item, unused-ignore]
        "status_key": _fmt_status_key,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "color": fmt_color,  # type: ignore[dict-item, unused-ignore]
        "status_key": _fmt_status_key,  # type: ignore[dict-item, unused-ignore]
    }
    form_columns = [
        PortalTaskColumn.position,
        PortalTaskColumn.title,
        PortalTaskColumn.status_key,
        PortalTaskColumn.jira_status_id,
        PortalTaskColumn.color,
        PortalTaskColumn.exclude_from_kpi,
    ]
    form_args = {
        "color": {"widget": ColorPickerWidget(), "label": "Цвет"},
        "title": {"label": "Заголовок"},
        "status_key": {"label": "Ключ статуса"},
        "jira_status_id": {"label": "ID статуса Jira (AUTASKS)"},
        "position": {"label": "Порядок"},
        "exclude_from_kpi": {"label": "Исключить из KPI"},
    }

    can_view_details = True
