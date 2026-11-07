from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from starlette.requests import Request

from app.admin.formatters import fmt_datetime, fmt_payment_category
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_FINANCE
from app.infrastructure.db.models.portal_finance import PortalInvoice, PortalPayment
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalPaymentAdmin(ModelView, model=PortalPayment):
    name = "Платёж"
    name_plural = "Платежи"
    icon = "fa-solid fa-money-bill-wave"
    category = SQLADMIN_CATEGORY_FINANCE

    form_ajax_refs = {
        "invoice": {
            "fields": (PortalInvoice.title,),
            "order_by": PortalInvoice.created_at,
        },
        "author_profile": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email, PortalUserProfile.username),
            "order_by": PortalUserProfile.full_name,
        },
    }

    form_columns = [
        "invoice",
        PortalPayment.amount,
        PortalPayment.currency,
        PortalPayment.payment_category,
        PortalPayment.paid_at,
        PortalPayment.note,
        "author_profile",
    ]

    column_list = [
        PortalPayment.amount,
        PortalPayment.currency,
        "invoice",
        PortalPayment.payment_category,
        PortalPayment.paid_at,
        "author_profile",
        PortalPayment.created_at,
    ]
    column_details_list = [
        PortalPayment.amount,
        PortalPayment.currency,
        "invoice",
        PortalPayment.payment_category,
        PortalPayment.paid_at,
        PortalPayment.note,
        "author_profile",
        PortalPayment.author_sub,
        PortalPayment.created_at,
    ]
    column_sortable_list = [PortalPayment.created_at, PortalPayment.paid_at]
    column_default_sort = [(PortalPayment.created_at, True)]
    column_formatters = {
        "payment_category": fmt_payment_category,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "payment_category": fmt_payment_category,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "invoice": "Счёт",
        "invoice_id": "Счёт (идентификатор)",
        "amount": "Сумма",
        "currency": "Валюта",
        "paid_at": "Дата платежа",
        "note": "Примечание",
        "payment_category": "Категория",
        "author_profile": "Автор",
        "author_sub": "Автор (sub)",
        "created_at": "Создан",
    }
    can_view_details = True

    async def on_model_change(
        self, data: dict[str, Any], model: PortalPayment, is_created: bool, request: Request
    ) -> None:
        if model.author_profile is not None:
            model.author_sub = model.author_profile.sub
