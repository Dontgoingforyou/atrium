from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from starlette.requests import Request

from app.admin.formatters import fmt_datetime, fmt_procurement_status
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_FINANCE
from app.infrastructure.db.models.portal_finance import PortalCounterparty, PortalProcurementRequest
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalProcurementRequestAdmin(ModelView, model=PortalProcurementRequest):
    name = "Закупочная заявка"
    name_plural = "Закупочные заявки"
    icon = "fa-solid fa-cart-shopping"
    category = SQLADMIN_CATEGORY_FINANCE

    form_ajax_refs = {
        "counterparty": {
            "fields": (PortalCounterparty.name,),
            "order_by": PortalCounterparty.name,
        },
        "author_profile": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email, PortalUserProfile.username),
            "order_by": PortalUserProfile.full_name,
        },
    }

    form_columns = [
        PortalProcurementRequest.title,
        PortalProcurementRequest.description,
        PortalProcurementRequest.status,
        "counterparty",
        PortalProcurementRequest.amount,
        PortalProcurementRequest.currency,
        PortalProcurementRequest.document_id,
        "author_profile",
    ]

    column_list = [
        PortalProcurementRequest.title,
        PortalProcurementRequest.status,
        "counterparty",
        PortalProcurementRequest.amount,
        PortalProcurementRequest.currency,
        PortalProcurementRequest.author_sub,
        PortalProcurementRequest.created_at,
    ]
    column_details_list = [
        PortalProcurementRequest.title,
        PortalProcurementRequest.description,
        PortalProcurementRequest.status,
        "counterparty",
        PortalProcurementRequest.counterparty_id,
        PortalProcurementRequest.amount,
        PortalProcurementRequest.currency,
        PortalProcurementRequest.document_id,
        "author_profile",
        PortalProcurementRequest.author_sub,
        PortalProcurementRequest.created_at,
        PortalProcurementRequest.updated_at,
    ]
    column_sortable_list = [
        PortalProcurementRequest.created_at,
        PortalProcurementRequest.status,
        PortalProcurementRequest.updated_at,
    ]
    column_default_sort = [(PortalProcurementRequest.created_at, True)]
    column_formatters = {
        "status": fmt_procurement_status,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "status": fmt_procurement_status,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "title": "Название",
        "description": "Описание",
        "status": "Статус",
        "counterparty": "Контрагент",
        "counterparty_id": "Контрагент (ID)",
        "amount": "Сумма",
        "currency": "Валюта",
        "document_id": "Документ (ID)",
        "author_profile": "Автор",
        "author_sub": "Автор (sub)",
        "created_at": "Создана",
        "updated_at": "Изменена",
    }
    can_view_details = True

    async def on_model_change(
        self, data: dict[str, Any], model: PortalProcurementRequest, is_created: bool, request: Request
    ) -> None:
        if model.author_profile is not None:
            model.author_sub = model.author_profile.sub
