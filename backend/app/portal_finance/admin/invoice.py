from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from starlette.requests import Request

from app.admin.formatters import fmt_datetime, fmt_invoice_status, fmt_invoice_type
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_FINANCE
from app.infrastructure.db.models.portal_finance import PortalContract, PortalInvoice
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalInvoiceAdmin(ModelView, model=PortalInvoice):
    name = "Счёт / Акт"
    name_plural = "Счета и акты"
    icon = "fa-solid fa-file-invoice"
    category = SQLADMIN_CATEGORY_FINANCE

    form_ajax_refs = {
        "contract": {
            "fields": (PortalContract.title,),
            "order_by": PortalContract.created_at,
        },
        "author_profile": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email, PortalUserProfile.username),
            "order_by": PortalUserProfile.full_name,
        },
    }

    form_columns = [
        PortalInvoice.title,
        PortalInvoice.invoice_type,
        "contract",
        PortalInvoice.amount,
        PortalInvoice.currency,
        PortalInvoice.issue_date,
        PortalInvoice.due_date,
        PortalInvoice.status,
        "author_profile",
    ]

    column_list = [
        PortalInvoice.title,
        PortalInvoice.invoice_type,
        "contract",
        PortalInvoice.amount,
        PortalInvoice.currency,
        PortalInvoice.status,
        PortalInvoice.due_date,
        PortalInvoice.created_at,
    ]
    column_details_list = [
        PortalInvoice.title,
        PortalInvoice.invoice_type,
        "contract",
        PortalInvoice.amount,
        PortalInvoice.currency,
        PortalInvoice.issue_date,
        PortalInvoice.due_date,
        PortalInvoice.status,
        "author_profile",
        PortalInvoice.author_sub,
        PortalInvoice.created_at,
        PortalInvoice.updated_at,
    ]
    column_sortable_list = [PortalInvoice.created_at, PortalInvoice.due_date, PortalInvoice.status]
    column_default_sort = [(PortalInvoice.created_at, True)]
    column_formatters = {
        "invoice_type": fmt_invoice_type,  # type: ignore[dict-item, unused-ignore]
        "status": fmt_invoice_status,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "invoice_type": fmt_invoice_type,  # type: ignore[dict-item, unused-ignore]
        "status": fmt_invoice_status,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "title": "Название",
        "invoice_type": "Тип",
        "contract": "Договор",
        "contract_id": "Договор (идентификатор)",
        "amount": "Сумма",
        "currency": "Валюта",
        "issue_date": "Дата выставления",
        "due_date": "Дата оплаты",
        "status": "Статус",
        "author_profile": "Автор",
        "author_sub": "Автор (sub)",
        "payments": "Платежи",
        "created_at": "Создан",
        "updated_at": "Изменён",
    }
    can_view_details = True

    async def on_model_change(
        self, data: dict[str, Any], model: PortalInvoice, is_created: bool, request: Request
    ) -> None:
        if model.author_profile is not None:
            model.author_sub = model.author_profile.sub
