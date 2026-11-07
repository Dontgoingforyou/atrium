"""SQLAdmin-вьюхи для связи документ-тег и истории изменений документа."""

from __future__ import annotations

from typing import Any

from sqladmin import ModelView

from app.admin.formatters import fmt_datetime, fmt_diff
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_DOCUMENTS
from app.infrastructure.db.models.portal_document import PortalDocumentHistory, PortalDocumentTag


def _fmt_editor(model: Any, attr: str) -> str:
    profile = getattr(model, "changed_by_profile", None)
    name = (profile.full_name if profile else None) or model.changed_by_display_name
    email = (profile.email if profile else None) or model.changed_by_email
    if name and email:
        return f"{name} ({email})"
    if email:
        return str(email)
    if name:
        return str(name)
    sub = model.changed_by_sub
    return str(sub) if sub else "—"


class PortalDocumentTagAdmin(ModelView, model=PortalDocumentTag):
    name = "Связь документ–тег"
    name_plural = "Связи документ–тег"
    icon = "fa-solid fa-link"
    category = SQLADMIN_CATEGORY_DOCUMENTS

    form_excluded_columns = ["document_id", "tag_id"]

    column_list = ["document", "tag"]
    column_details_list = ["document", "tag"]
    column_labels = {
        "document_id": "Документ",
        "tag_id": "Тег",
        "document": "Документ",
        "tag": "Тег",
    }
    column_sortable_list = ["document", "tag"]

    can_create = True
    can_edit = False
    can_delete = True
    can_view_details = True


class PortalDocumentHistoryAdmin(ModelView, model=PortalDocumentHistory):
    name = "История изменений"
    name_plural = "История изменений"
    icon = "fa-solid fa-clock-rotate-left"
    category = SQLADMIN_CATEGORY_DOCUMENTS

    column_list = [
        "document",
        PortalDocumentHistory.changed_by_display_name,
        PortalDocumentHistory.changed_at,
    ]
    column_details_list = [
        "document",
        PortalDocumentHistory.changed_by_display_name,
        PortalDocumentHistory.changed_by_email,
        PortalDocumentHistory.changed_at,
        PortalDocumentHistory.diff,
    ]
    column_formatters = {
        "changed_by_display_name": _fmt_editor,  # type: ignore[dict-item, unused-ignore]
        "changed_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "changed_by_display_name": _fmt_editor,  # type: ignore[dict-item, unused-ignore]
        "changed_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "diff": fmt_diff,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "document": "Документ",
        "document_id": "Документ",
        "changed_by_sub": "Идентификатор в SSO",
        "changed_by_display_name": "Редактор",
        "changed_by_email": "Почта редактора",
        "changed_at": "Время изменения",
        "diff": "Что изменилось",
    }

    can_create = False
    can_edit = False
    can_delete = True
    can_view_details = True
