from __future__ import annotations

import logging
from typing import Any

from sqladmin import ModelView
from wtforms.validators import DataRequired, Optional
from wtforms.widgets import TextInput

from app.admin.formatters import fmt_color, fmt_datetime
from app.admin.model_converter import AtriumAdminModelConverter
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_DOCUMENTS
from app.infrastructure.db.models.portal_document import PortalDocument, PortalTag
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.infrastructure.db.session import async_session_factory
from app.portal_documents.services.portal_document import write_document_history
from app.portal_documents.services.portal_document_realtime import publish_document_mutation
from app.services import portal_tags as portal_tags_svc

logger = logging.getLogger(__name__)


class ColorPickerWidget(TextInput):
    """Виджет для выбора цвета через браузерную палитру."""

    input_type = "color"


def _fmt_author(model: Any, attr: str) -> str:
    name = model.author_display_name
    email = model.author_email
    if name and email:
        return f"{name} ({email})"
    if email:
        return str(email)
    if name:
        return str(name)
    return "—"


def _normalize_document_tags(data: dict[str, Any]) -> None:
    """WTForms присылает теги списком строк или CSV — свести к чистому списку слагов/имён."""
    tags = data.get("tags")
    if tags is None:
        return
    if isinstance(tags, (list, tuple, set)):
        data["tags"] = [str(x).strip() for x in tags if x is not None and str(x).strip()]
    elif isinstance(tags, str):
        data["tags"] = [p.strip() for p in tags.split(",") if p.strip()]


def _resolve_document_author(data: dict[str, Any], request: Any, *, is_created: bool) -> None:
    """Дефолт «автор = текущий админ» — только при создании: правка чужого документа
    не должна молча переписывать его настоящего автора, если AJAX-пикер не тронут.
    """
    author_user = data.get("author_user")
    if author_user is not None and hasattr(author_user, "sub"):
        data["author_sub"] = author_user.sub
        data["author_display_name"] = author_user.full_name
        data["author_email"] = author_user.email
    elif is_created:
        data.setdefault("author_sub", request.session.get("admin_sub", ""))
        data.setdefault("author_display_name", request.session.get("admin_full_name"))
        data.setdefault("author_email", request.session.get("admin_email"))


def _resolve_document_owner(data: dict[str, Any]) -> None:
    """В отличие от автора — без дефолта из сессии: владелец не обязан совпадать с редактором."""
    owner_user = data.get("owner_user")
    if owner_user is not None and hasattr(owner_user, "sub"):
        data["owner_sub"] = owner_user.sub
        data["owner_email"] = owner_user.email


class PortalTagAdmin(ModelView, model=PortalTag):
    name = "Тег"
    name_plural = "Теги"
    icon = "fa-solid fa-tag"
    category = SQLADMIN_CATEGORY_DOCUMENTS
    category_icon = "fa-solid fa-folder-open"

    column_list = [PortalTag.name, PortalTag.slug, PortalTag.color]
    column_searchable_list = [PortalTag.name, PortalTag.slug]
    column_sortable_list = [PortalTag.name, PortalTag.slug]
    column_default_sort = [(PortalTag.name, False)]
    column_labels = {
        "id": "Внутренний номер",
        "name": "Название",
        "slug": "Код в URL",
        "color": "Цвет",
        "documents": "Документы",
    }
    column_formatters = {
        "color": fmt_color,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "color": fmt_color,  # type: ignore[dict-item, unused-ignore]
    }
    column_details_list = [PortalTag.name, PortalTag.slug, PortalTag.color, "documents"]
    form_excluded_columns = ["slug", "documents", "version"]
    form_args = {"color": {"widget": ColorPickerWidget()}}

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    async def on_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Any) -> None:
        from app.admin.cas_version import bump_cas_version_on_edit

        bump_cas_version_on_edit(data, model, is_created=is_created)
        raw_name: str = data.get("name") or ""
        if not raw_name.strip():
            return
        exclude_id = None if is_created else model.id
        async with async_session_factory() as session:
            display, slug = await portal_tags_svc.resolve_name_and_slug_for_admin_form(
                session,
                raw_name=raw_name,
                exclude_tag_id=exclude_id,
            )
        data["name"] = display
        data["slug"] = slug


class PortalDocumentAdmin(ModelView, model=PortalDocument):
    name = "Документ"
    name_plural = "Документы"
    icon = "fa-solid fa-file-lines"
    category = SQLADMIN_CATEGORY_DOCUMENTS

    column_list = [
        PortalDocument.title,
        PortalDocument.author_display_name,
        PortalDocument.created_at,
        PortalDocument.updated_at,
    ]
    column_formatters = {
        "author_display_name": _fmt_author,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
        "updated_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_searchable_list = [
        PortalDocument.title,
        PortalDocument.author_display_name,
        PortalDocument.author_email,
    ]
    column_sortable_list = [
        PortalDocument.title,
        PortalDocument.created_at,
        PortalDocument.updated_at,
    ]
    column_default_sort = [(PortalDocument.created_at, True)]
    column_details_list = [
        PortalDocument.title,
        PortalDocument.body,
        PortalDocument.tags,
        PortalDocument.author_display_name,
        PortalDocument.author_email,
        PortalDocument.owner_email,
        PortalDocument.created_at,
        PortalDocument.updated_at,
    ]
    column_labels = {
        "id": "Внутренний номер",
        "title": "Заголовок",
        "icon_emoji": "Эмодзи в дереве",
        "body": "Содержимое",
        "tags": "Теги",
        "author_sub": "Идентификатор автора",
        "author_display_name": "Автор",
        "author_email": "Почта автора",
        "author_user": "Автор",
        "owner_sub": "Идентификатор владельца",
        "owner_email": "Почта владельца",
        "owner_user": "Владелец",
        "history": "История изменений",
        "created_at": "Создан",
        "updated_at": "Изменён",
    }
    form_excluded_columns = [
        "id",
        "history",
        "author_sub",
        "author_display_name",
        "author_email",
        "owner_sub",
        "owner_email",
        "created_at",
        "updated_at",
        "deleted_at",
        "deleted_by_sub",
        "deleted_by_display_name",
        "deleted_by_email",
        "sort_order",
        "version",
    ]
    # Тип/статус: русские подписи и значения БД — см. AtriumAdminModelConverter
    form_converter = AtriumAdminModelConverter
    # M2M: у sqladmin QuerySelectMultipleField при data=None не рендерит options; Ajax обходит баг
    form_ajax_refs = {
        "tags": {
            "fields": ("name", "slug"),
            "order_by": [PortalTag.name],
        },
        "author_user": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email),
            "order_by": PortalUserProfile.full_name,
        },
        "owner_user": {
            "fields": (PortalUserProfile.full_name, PortalUserProfile.email),
            "order_by": PortalUserProfile.full_name,
        },
    }
    form_args = {
        "author_user": {"validators": [DataRequired()], "label": "Автор"},
        "owner_user": {"validators": [Optional()], "label": "Владелец"},
    }

    can_create = True
    can_edit = True
    can_delete = False
    can_view_details = True

    async def on_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Any) -> None:
        from app.admin.cas_version import bump_cas_version_on_edit

        bump_cas_version_on_edit(data, model, is_created=is_created)
        _normalize_document_tags(data)
        _resolve_document_author(data, request, is_created=is_created)
        _resolve_document_owner(data)

    async def after_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Any) -> None:
        """Аудит и realtime-уведомление после сохранения — как в REST API (см. portal_document_mutations).

        Побочный эффект best-effort: документ уже сохранён (после commit sqladmin),
        поэтому сбой истории/публикации не должен превращать успешное сохранение в ошибку 500.
        """
        try:
            changed_by_sub = request.session.get("admin_sub") or ""
            async with async_session_factory() as session:
                await write_document_history(
                    session,
                    model.id,
                    changed_by_sub,
                    {"action": {"old": None, "new": "created" if is_created else "updated"}},
                    changed_by_display_name=request.session.get("admin_full_name"),
                    changed_by_email=request.session.get("admin_email"),
                )
                await session.commit()
            await publish_document_mutation(
                document_id=model.id,
                parent_document_id=model.parent_document_id,
            )
        except Exception:
            logger.exception(
                "Не удалось записать историю/оповестить о правке документа %s через админку",
                model.id,
            )
