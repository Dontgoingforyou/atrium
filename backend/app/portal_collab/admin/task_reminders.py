from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from app.admin.formatters import fmt_datetime
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_TASKS
from app.infrastructure.db.models.portal_task_reminder_sent import PortalTaskReminderSent
from app.portal_collab.admin.formatters import fmt_recipient_sub


class PortalTaskReminderSentAdmin(ModelView, model=PortalTaskReminderSent):
    """Журнал идемпотентности напоминаний о сроке — просмотр и очистка."""

    name = "Отправленное напоминание о сроке"
    name_plural = "Напоминания о сроке задач"
    icon = "fa-solid fa-clock"
    category = SQLADMIN_CATEGORY_TASKS

    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True

    column_list = [
        PortalTaskReminderSent.task_id,
        PortalTaskReminderSent.recipient_sub,
        PortalTaskReminderSent.reminder_kind,
        PortalTaskReminderSent.due_at_snapshot,
        PortalTaskReminderSent.sent_at,
    ]
    column_details_list = [
        PortalTaskReminderSent.task_id,
        PortalTaskReminderSent.recipient_sub,
        PortalTaskReminderSent.reminder_kind,
        PortalTaskReminderSent.due_at_snapshot,
        PortalTaskReminderSent.sent_at,
    ]
    column_searchable_list = [PortalTaskReminderSent.recipient_sub, PortalTaskReminderSent.reminder_kind]
    column_sortable_list = [PortalTaskReminderSent.sent_at, PortalTaskReminderSent.due_at_snapshot]
    column_default_sort = [(PortalTaskReminderSent.sent_at, True)]
    column_formatters = {
        "recipient_sub": fmt_recipient_sub,  # type: ignore[dict-item, unused-ignore]
        "due_at_snapshot": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "sent_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "recipient_sub": fmt_recipient_sub,  # type: ignore[dict-item, unused-ignore]
        "due_at_snapshot": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "sent_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "task_id": "Задача (ID)",
        "recipient_sub": "Получатель",
        "reminder_kind": "Этап",
        "due_at_snapshot": "Срок на момент отправки",
        "sent_at": "Отправлено",
    }

    def list_query(self, request: Request) -> Any:
        return select(PortalTaskReminderSent).options(
            selectinload(PortalTaskReminderSent.task),
            selectinload(PortalTaskReminderSent.recipient_profile),
        )

    def details_query(self, request: Request) -> Any:
        return select(PortalTaskReminderSent).options(
            selectinload(PortalTaskReminderSent.task),
            selectinload(PortalTaskReminderSent.recipient_profile),
        )
