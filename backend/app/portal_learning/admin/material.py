from __future__ import annotations

from typing import Any

from sqladmin import ModelView
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms import SelectField

from app.admin.enum_labels import LEARNING_MATERIAL_STATUS_LABELS_RU, LEARNING_MATERIAL_TYPE_LABELS_RU
from app.admin.formatters import fmt_datetime, fmt_learning_material_status, fmt_learning_material_type
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_LEARNING
from app.infrastructure.db.models.portal_learning import PortalLearningMaterial, PortalLearningMaterialIdpGroup
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.admin.formatters import fmt_created_by

_MATERIAL_TYPE_CHOICES = [(k, v) for k, v in LEARNING_MATERIAL_TYPE_LABELS_RU.items()]
_MATERIAL_STATUS_CHOICES = [(k, v) for k, v in LEARNING_MATERIAL_STATUS_LABELS_RU.items()]


def _fmt_idp_groups(model: Any, attr: str) -> str:
    rows = getattr(model, attr, None) or []
    if not rows:
        return "Все (по настройкам M2M)"
    return ", ".join((r.idp_group if isinstance(r, PortalLearningMaterialIdpGroup) else str(r)) for r in rows)


class PortalLearningMaterialAdmin(ModelView, model=PortalLearningMaterial):
    name = "Учебный материал"
    name_plural = "Учебные материалы"
    icon = "fa-solid fa-book"
    category = SQLADMIN_CATEGORY_LEARNING
    category_icon = "fa-solid fa-graduation-cap"

    form_ajax_refs = {
        "created_by_profile": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email, PortalUserProfile.username),
            "order_by": PortalUserProfile.full_name,
        },
    }
    form_overrides = {
        "material_type": SelectField,
        "status": SelectField,
    }
    form_args = {
        "material_type": {"choices": _MATERIAL_TYPE_CHOICES, "coerce": str},
        "status": {"choices": _MATERIAL_STATUS_CHOICES, "coerce": str},
    }
    # Группы Keycloak — в разделе «Материал: группа Keycloak» (idp_group_rows не в форме)
    form_columns = [
        PortalLearningMaterial.title,
        PortalLearningMaterial.body,
        PortalLearningMaterial.material_type,
        PortalLearningMaterial.status,
        "created_by_profile",
    ]

    column_list = [
        PortalLearningMaterial.title,
        PortalLearningMaterial.material_type,
        PortalLearningMaterial.status,
        "idp_group_rows",
        PortalLearningMaterial.created_by_sub,
        PortalLearningMaterial.created_at,
    ]
    column_labels = {
        "title": "Название",
        "body": "Содержание",
        "material_type": "Тип",
        "status": "Статус",
        "idp_group_rows": "Доступ (группы)",
        "created_by_sub": "Автор",
        "created_by_profile": "Автор (профиль)",
        "quizzes": "Связанные тесты",
        "created_at": "Создан",
        "updated_at": "Обновлён",
    }
    column_formatters = {
        "material_type": fmt_learning_material_type,  # type: ignore[dict-item, unused-ignore]
        "status": fmt_learning_material_status,  # type: ignore[dict-item, unused-ignore]
        "idp_group_rows": _fmt_idp_groups,  # type: ignore[dict-item, unused-ignore]
        "created_by_sub": fmt_created_by,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "material_type": fmt_learning_material_type,  # type: ignore[dict-item, unused-ignore]
        "status": fmt_learning_material_status,  # type: ignore[dict-item, unused-ignore]
        "idp_group_rows": _fmt_idp_groups,  # type: ignore[dict-item, unused-ignore]
        "created_by_sub": fmt_created_by,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_details_list = [
        PortalLearningMaterial.title,
        PortalLearningMaterial.body,
        PortalLearningMaterial.material_type,
        PortalLearningMaterial.status,
        "idp_group_rows",
        PortalLearningMaterial.created_by_sub,
        PortalLearningMaterial.created_at,
        PortalLearningMaterial.updated_at,
    ]
    can_view_details = True
    column_searchable_list = [PortalLearningMaterial.title]
    column_sortable_list = [
        PortalLearningMaterial.title,
        PortalLearningMaterial.material_type,
        PortalLearningMaterial.status,
        PortalLearningMaterial.created_at,
    ]
    column_default_sort = [(PortalLearningMaterial.created_at, True)]

    def list_query(self, request: Request) -> Any:
        return select(PortalLearningMaterial).options(
            selectinload(PortalLearningMaterial.idp_group_rows),
            selectinload(PortalLearningMaterial.created_by_profile),
        )

    def count_query(self, request: Request) -> Any:
        return select(func.count(PortalLearningMaterial.id))

    def details_query(self, request: Request) -> Any:
        return self.form_edit_query(request).options(
            selectinload(PortalLearningMaterial.idp_group_rows),
            selectinload(PortalLearningMaterial.created_by_profile),
        )

    async def on_model_change(
        self, data: dict[str, Any], model: PortalLearningMaterial, is_created: bool, request: Request
    ) -> None:
        from app.admin.cas_version import bump_cas_version_on_edit

        bump_cas_version_on_edit(data, model, is_created=is_created)
        if model.created_by_profile is not None:
            model.created_by_sub = model.created_by_profile.sub
