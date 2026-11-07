from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from wtforms.validators import DataRequired

from app.admin.formatters import fmt_agreement_status, fmt_datetime
from app.admin.model_converter import CosmoletAdminModelConverter
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_FINANCE
from app.infrastructure.db.models.portal_agreement import PortalAgreement
from app.infrastructure.db.models.portal_chat import PortalChatMessage
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.admin.formatters import fmt_created_by


def _fmt_agreement_body_preview(model: Any, attr: str) -> str:
    text = getattr(model, attr, "") or ""
    return text[:120] + ("…" if len(text) > 120 else "")


def _normalize_single_fk(data: dict[str, Any], key: str) -> None:
    if key not in data:
        return
    val = data[key]
    if isinstance(val, (list, tuple, set)):
        raw = [x for x in val if x is not None and str(x).strip() not in ("", "__None")]
        data[key] = raw[0] if raw else None
    v = data[key]
    if v in (None, "", "__None") or (isinstance(v, str) and not v.strip()):
        data[key] = None


class PortalAgreementAdmin(ModelView, model=PortalAgreement):
    name = "Договорённость"
    name_plural = "Договорённости"
    icon = "fa-solid fa-handshake"
    category = SQLADMIN_CATEGORY_FINANCE
    category_icon = "fa-solid fa-landmark"

    form_converter = CosmoletAdminModelConverter
    form_excluded_columns = [
        "created_by_profile",
        "created_by_sub",
        "source_message_id",
        "document_id",
        "task_id",
        "created_at",
        "updated_at",
    ]
    form_ajax_refs = {
        "created_by_user": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email),
            "order_by": PortalUserProfile.full_name,
        },
        "document": {
            "fields": (PortalDocument.title,),
            "order_by": PortalDocument.title,
        },
        "task": {
            "fields": (PortalTask.title,),
            "order_by": PortalTask.title,
        },
        "source_message": {
            "fields": (PortalChatMessage.body, PortalChatMessage.created_at),
            "order_by": PortalChatMessage.created_at,
        },
    }
    form_args = {
        "created_by_user": {"validators": [DataRequired()], "label": "Создатель"},
    }

    column_list = [
        PortalAgreement.body,
        PortalAgreement.status,
        "document",
        "task",
        "source_message",
        PortalAgreement.created_by_sub,
        PortalAgreement.created_at,
    ]
    column_details_list = [
        PortalAgreement.body,
        PortalAgreement.status,
        "source_message",
        "document",
        "task",
        PortalAgreement.created_by_sub,
        PortalAgreement.created_at,
        PortalAgreement.updated_at,
    ]
    column_formatters = {
        "created_by_sub": fmt_created_by,  # type: ignore[dict-item, unused-ignore]
        "status": fmt_agreement_status,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "body": _fmt_agreement_body_preview,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "created_by_sub": fmt_created_by,  # type: ignore[dict-item, unused-ignore]
        "status": fmt_agreement_status,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_default_sort = [(PortalAgreement.created_at, True)]
    column_labels = {
        "id": "Внутренний номер",
        "body": "Текст",
        "status": "Статус",
        "source_message_id": "Исходное сообщение (идентификатор)",
        "source_message": "Исходное сообщение",
        "document_id": "Документ (идентификатор)",
        "task_id": "Задача (идентификатор)",
        "created_by_sub": "Создатель",
        "created_by_user": "Создатель",
        "created_at": "Создана",
        "updated_at": "Изменена",
        "document": "Документ",
        "task": "Задача",
    }
    can_view_details = True

    async def on_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Any) -> None:
        for fk in ("document", "task", "source_message"):
            _normalize_single_fk(data, fk)

        cu = data.get("created_by_user")
        if cu is not None and hasattr(cu, "sub"):
            data["created_by_sub"] = cu.sub
