from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from starlette.requests import Request

from app.admin.formatters import fmt_contract_status, fmt_contract_type, fmt_datetime
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_FINANCE
from app.infrastructure.db.models.portal_finance import PortalContract, PortalCounterparty
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalContractAdmin(ModelView, model=PortalContract):
    name = "Договор"
    name_plural = "Договоры"
    icon = "fa-solid fa-file-contract"
    category = SQLADMIN_CATEGORY_FINANCE

    form_ajax_refs = {
        "counterparty": {
            "fields": (PortalCounterparty.name, PortalCounterparty.inn),
            "order_by": PortalCounterparty.name,
        },
        "author_profile": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email, PortalUserProfile.username),
            "order_by": PortalUserProfile.full_name,
        },
        "owner_profile": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email, PortalUserProfile.username),
            "order_by": PortalUserProfile.full_name,
        },
    }

    form_columns = [
        PortalContract.title,
        PortalContract.contract_type,
        "counterparty",
        PortalContract.amount,
        PortalContract.currency,
        PortalContract.start_date,
        PortalContract.end_date,
        PortalContract.status,
        PortalContract.document_id,
        "author_profile",
        "owner_profile",
    ]

    column_list = [
        PortalContract.title,
        "counterparty",
        PortalContract.status,
        PortalContract.amount,
        PortalContract.currency,
        PortalContract.start_date,
        PortalContract.end_date,
        PortalContract.created_at,
    ]
    column_details_list = [
        PortalContract.title,
        PortalContract.contract_type,
        "counterparty",
        PortalContract.amount,
        PortalContract.currency,
        PortalContract.start_date,
        PortalContract.end_date,
        PortalContract.status,
        PortalContract.document_id,
        "author_profile",
        PortalContract.author_sub,
        "owner_profile",
        PortalContract.owner_sub,
        PortalContract.created_at,
        PortalContract.updated_at,
    ]
    column_searchable_list = [PortalContract.title]
    column_sortable_list = [PortalContract.created_at, PortalContract.status]
    column_default_sort = [(PortalContract.created_at, True)]
    column_formatters = {
        "status": fmt_contract_status,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "contract_type": fmt_contract_type,  # type: ignore[dict-item, unused-ignore]
        "status": fmt_contract_status,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_labels = {
        "id": "Внутренний номер",
        "title": "Название",
        "contract_type": "Тип",
        "counterparty": "Контрагент",
        "counterparty_id": "Контрагент (идентификатор)",
        "amount": "Сумма",
        "currency": "Валюта",
        "start_date": "Дата начала",
        "end_date": "Дата окончания",
        "status": "Статус",
        "document_id": "Документ (ID)",
        "document": "Документ",
        "author_profile": "Автор",
        "author_sub": "Автор (sub)",
        "owner_profile": "Владелец",
        "owner_sub": "Владелец (sub)",
        "invoices": "Счета и акты",
        "created_at": "Создан",
        "updated_at": "Изменён",
    }
    can_view_details = True

    async def on_model_change(
        self, data: dict[str, Any], model: PortalContract, is_created: bool, request: Request
    ) -> None:
        if model.author_profile is not None:
            model.author_sub = model.author_profile.sub
        if model.owner_profile is not None:
            model.owner_sub = model.owner_profile.sub
