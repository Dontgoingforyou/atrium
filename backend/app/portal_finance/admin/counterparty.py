from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from starlette.requests import Request

from app.admin.formatters import fmt_counterparty_type, fmt_datetime
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_FINANCE
from app.infrastructure.db.models.portal_finance import PortalCounterparty
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalCounterpartyAdmin(ModelView, model=PortalCounterparty):
    name = "Контрагент"
    name_plural = "Контрагенты"
    icon = "fa-solid fa-building"
    category = SQLADMIN_CATEGORY_FINANCE

    form_ajax_refs = {
        "author_profile": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email, PortalUserProfile.username),
            "order_by": PortalUserProfile.full_name,
        },
    }

    form_columns = [
        PortalCounterparty.name,
        PortalCounterparty.inn,
        PortalCounterparty.counterparty_type,
        PortalCounterparty.contact_email,
        PortalCounterparty.contact_phone,
        PortalCounterparty.note,
        PortalCounterparty.is_active,
        "author_profile",
    ]

    column_list = [
        PortalCounterparty.name,
        PortalCounterparty.inn,
        PortalCounterparty.counterparty_type,
        PortalCounterparty.contact_email,
        PortalCounterparty.is_active,
        PortalCounterparty.created_at,
    ]
    column_details_list = [
        PortalCounterparty.name,
        PortalCounterparty.inn,
        PortalCounterparty.counterparty_type,
        PortalCounterparty.contact_email,
        PortalCounterparty.contact_phone,
        PortalCounterparty.note,
        PortalCounterparty.is_active,
        "author_profile",
        PortalCounterparty.author_sub,
        PortalCounterparty.created_at,
        PortalCounterparty.updated_at,
    ]
    column_searchable_list = [PortalCounterparty.name, PortalCounterparty.inn]
    column_sortable_list = [PortalCounterparty.name, PortalCounterparty.created_at]
    column_default_sort = [(PortalCounterparty.name, False)]
    column_formatters = {
        "counterparty_type": fmt_counterparty_type,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "counterparty_type": fmt_counterparty_type,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "name": "Наименование",
        "inn": "ИНН",
        "counterparty_type": "Тип",
        "contact_email": "Email",
        "contact_phone": "Телефон",
        "note": "Примечание",
        "is_active": "Активен",
        "author_profile": "Создатель",
        "author_sub": "Создатель (sub)",
        "contracts": "Договоры",
        "created_at": "Создан",
        "updated_at": "Изменён",
    }
    can_view_details = True

    async def on_model_change(
        self, data: dict[str, Any], model: PortalCounterparty, is_created: bool, request: Request
    ) -> None:
        if model.author_profile is not None:
            model.author_sub = model.author_profile.sub
