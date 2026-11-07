from __future__ import annotations

import logging
from typing import Any

from markupsafe import Markup
from sqladmin import ModelView
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.requests import Request
from wtforms.validators import ValidationError

from app.admin.formatters import fmt_color, fmt_datetime
from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_SPECIALISTS
from app.admin.views.documents import ColorPickerWidget
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_specialist_status import PortalSpecialistStatus
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile

logger = logging.getLogger(__name__)


def profile_display(profile: Any, _sub_fallback: str = "") -> str:
    """Возвращает «Имя (email)» из профиля."""
    if profile is None:
        return "—"
    name = getattr(profile, "full_name", None) or ""
    email = getattr(profile, "email", None) or ""
    if name and email:
        return f"{name} ({email})"
    return name or email or "—"


def _fmt_manager(model: Any, attr: str) -> str:
    return profile_display(getattr(model, "manager_profile", None), getattr(model, "manager_sub", ""))


def _fmt_specialist(model: Any, attr: str) -> str:
    return profile_display(getattr(model, "specialist_profile", None), getattr(model, "specialist_sub", ""))


def _fmt_status(model: Any, attr: str) -> Markup:
    """Отображает связанный статус: цветной кружок + название."""
    status = getattr(model, "status", None)
    if status is None:
        return Markup("—")
    color = Markup.escape(getattr(status, "color", "#888888"))
    title = Markup.escape(getattr(status, "title", "—"))
    return Markup(f'<span style="color:{color}">●</span>&nbsp;{title}')


def _fmt_column(model: Any, attr: str) -> str:
    """Возвращает заголовок колонки из связанного объекта или исходный key."""
    col = getattr(model, "column_obj", None)
    if col is not None:
        return str(getattr(col, "title", model.column_key))
    return str(getattr(model, "column_key", "—"))


class PortalSpecialistColumnAdmin(ModelView, model=PortalSpecialistColumn):
    name = "Колонка воронки"
    name_plural = "Колонки канбана (специалисты)"
    icon = "fa-solid fa-table-columns"
    category = SQLADMIN_CATEGORY_SPECIALISTS
    category_icon = "fa-solid fa-user-tie"

    column_list = [
        PortalSpecialistColumn.position,
        PortalSpecialistColumn.title,
        PortalSpecialistColumn.key,
        PortalSpecialistColumn.color,
    ]
    column_details_list = [
        PortalSpecialistColumn.id,
        PortalSpecialistColumn.position,
        PortalSpecialistColumn.title,
        PortalSpecialistColumn.key,
        PortalSpecialistColumn.color,
    ]
    column_default_sort = [(PortalSpecialistColumn.position, False)]
    column_sortable_list = [
        PortalSpecialistColumn.position,
        PortalSpecialistColumn.title,
        PortalSpecialistColumn.key,
    ]
    column_searchable_list = [PortalSpecialistColumn.title, PortalSpecialistColumn.key]
    column_labels = {
        "id": "Идентификатор",
        "key": "Ключ колонки",
        "title": "Заголовок",
        "color": "Цвет",
        "position": "Порядок",
    }
    column_formatters = {
        "color": fmt_color,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "color": fmt_color,  # type: ignore[dict-item, unused-ignore]
    }
    form_args = {
        "color": {"widget": ColorPickerWidget(), "label": "Цвет"},
        "title": {"label": "Заголовок"},
        "key": {"label": "Ключ колонки"},
        "position": {"label": "Порядок"},
    }
    form_excluded_columns = ["id"]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: Any,
        is_created: bool,
        request: Request,
    ) -> None:
        if not is_created:
            return
        key = str(data.get("key") or "").strip()
        if not key:
            raise ValidationError("Укажите уникальный ключ колонки (латиница, без пробелов).")
        from app.infrastructure.db.session import engine  # noqa: PLC0415

        async with AsyncSession(engine) as session:
            existing = await session.scalar(
                select(PortalSpecialistColumn.id).where(PortalSpecialistColumn.key == key).limit(1),
            )
        if existing is not None:
            raise ValidationError(f"Колонка с ключом «{key}» уже существует")

    async def insert_model(self, request: Request, data: dict[str, Any]) -> Any:
        try:
            return await super().insert_model(request, data)
        except IntegrityError as exc:
            if "uq_portal_specialist_column_key" in str(exc.orig):
                raise ValidationError("Колонка с таким ключом уже существует") from exc
            raise

    async def on_model_delete(self, model: Any, request: Request) -> None:
        """Не удалять колонку, если на ней есть закрепления (как REST delete_specialist_column)."""
        from app.infrastructure.db.session import engine  # noqa: PLC0415

        async with AsyncSession(engine) as session:
            entry_count: int = (
                await session.scalar(
                    select(func.count())
                    .select_from(PortalManagerSpecialist)
                    .where(PortalManagerSpecialist.column_key == model.key),
                )
                or 0
            )
        if entry_count > 0:
            raise ValidationError(
                f"Нельзя удалить колонку: на доске {entry_count} закреплений. "
                "Сначала переместите или снимите специалистов с доски."
            )


class PortalSpecialistStatusAdmin(ModelView, model=PortalSpecialistStatus):
    name = "Направление специалиста"
    name_plural = "Направления специалистов"
    icon = "fa-solid fa-circle-dot"
    category = SQLADMIN_CATEGORY_SPECIALISTS

    column_list = [
        PortalSpecialistStatus.title,
        PortalSpecialistStatus.color,
    ]
    column_details_list = [
        PortalSpecialistStatus.id,
        PortalSpecialistStatus.title,
        PortalSpecialistStatus.color,
    ]
    column_sortable_list = [PortalSpecialistStatus.title]
    column_default_sort = [(PortalSpecialistStatus.title, False)]
    column_searchable_list = [PortalSpecialistStatus.title]
    column_labels = {
        "id": "Идентификатор",
        "title": "Название",
        "color": "Цвет",
    }
    column_formatters = {
        "color": fmt_color,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "color": fmt_color,  # type: ignore[dict-item, unused-ignore]
    }
    form_args = {"color": {"widget": ColorPickerWidget()}}
    form_excluded_columns = ["id"]

    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True


class PortalManagerSpecialistAdmin(ModelView, model=PortalManagerSpecialist):
    """Не зарегистрирован в main.py: записи на доске ведутся через API, не SQLAdmin."""

    name = "Специалист на доске"
    name_plural = "Доска специалистов"
    icon = "fa-solid fa-users-between-lines"
    category = SQLADMIN_CATEGORY_SPECIALISTS

    column_list = [
        "manager_profile",
        "specialist_profile",
        PortalManagerSpecialist.column_key,
        PortalManagerSpecialist.position,
        PortalManagerSpecialist.created_at,
    ]
    column_details_list = [
        PortalManagerSpecialist.id,
        "manager_profile",
        "specialist_profile",
        PortalManagerSpecialist.column_key,
        PortalManagerSpecialist.position,
        "status",
        PortalManagerSpecialist.created_at,
    ]
    column_sortable_list = [
        PortalManagerSpecialist.column_key,
        PortalManagerSpecialist.position,
        PortalManagerSpecialist.created_at,
    ]
    column_default_sort = [(PortalManagerSpecialist.created_at, True)]
    column_searchable_list = [
        PortalManagerSpecialist.column_key,
    ]
    column_labels = {
        "id": "Идентификатор",
        "manager_profile": "Менеджер",
        "specialist_profile": "Специалист",
        "column_key": "Колонка",
        "position": "Позиция",
        "status": "Направление",
        "created_at": "Дата добавления",
    }
    column_formatters = {
        "manager_profile": _fmt_manager,  # type: ignore[dict-item, unused-ignore]
        "specialist_profile": _fmt_specialist,  # type: ignore[dict-item, unused-ignore]
        "column_key": _fmt_column,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "manager_profile": _fmt_manager,  # type: ignore[dict-item, unused-ignore]
        "specialist_profile": _fmt_specialist,  # type: ignore[dict-item, unused-ignore]
        "column_key": _fmt_column,  # type: ignore[dict-item, unused-ignore]
        "status": _fmt_status,  # type: ignore[dict-item, unused-ignore]
        "created_at": fmt_datetime,  # type: ignore[dict-item, unused-ignore]
    }
    form_excluded_columns = [
        "id",
        "created_at",
        "status",
        "manager_profile",
        "specialist_profile",
        "column_obj",
        "version",
    ]
    form_args = {}

    can_create = False
    can_edit = False
    can_delete = False
    can_view_details = True

    async def scaffold_form(self, form_rules: Any = None) -> Any:
        """Заменяет UUID-поля на SelectField с именами пользователей и колонок."""
        from wtforms import SelectField  # noqa: PLC0415

        from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn  # noqa: PLC0415
        from app.infrastructure.db.session import engine  # noqa: PLC0415

        form_class = await super().scaffold_form(form_rules)

        async with AsyncSession(engine) as session:
            profiles = list(
                (
                    await session.scalars(
                        select(PortalUserProfile).order_by(PortalUserProfile.full_name, PortalUserProfile.email)
                    )
                ).all()
            )
            columns = list(
                (await session.scalars(select(PortalSpecialistColumn).order_by(PortalSpecialistColumn.position))).all()
            )

        def _profile_choice(p: PortalUserProfile) -> tuple[str, str]:
            name = p.full_name or ""
            email = p.email or ""
            if name and email:
                label = f"{name} ({email})"
            else:
                label = name or email or p.sub[:16] + "…"
            return (p.sub, label)

        user_choices = [_profile_choice(p) for p in profiles]
        column_choices = [(c.key, c.title) for c in columns]

        form_class.manager_sub = SelectField(
            "Менеджер",
            choices=user_choices,
            description="Смена менеджера = перенос закрепления на другого пользователя",
        )
        form_class.specialist_sub = SelectField("Специалист", choices=user_choices)
        if column_choices:
            form_class.column_key = SelectField("Колонка", choices=column_choices)

        return form_class

    def list_query(self, request: Request) -> Any:
        """Загружать профили менеджера, специалиста и колонку только для страниц SQLAdmin."""
        return select(PortalManagerSpecialist).options(
            selectinload(PortalManagerSpecialist.manager_profile),
            selectinload(PortalManagerSpecialist.specialist_profile),
            selectinload(PortalManagerSpecialist.column_obj),
        )

    def details_query(self, request: Request) -> Any:
        """Загружать профили, статус и колонку только для страницы деталей SQLAdmin."""
        return select(PortalManagerSpecialist).options(
            selectinload(PortalManagerSpecialist.manager_profile),
            selectinload(PortalManagerSpecialist.specialist_profile),
            selectinload(PortalManagerSpecialist.status),
            selectinload(PortalManagerSpecialist.column_obj),
        )

    async def on_model_change(
        self,
        data: dict[str, Any],
        model: Any,
        is_created: bool,
        request: Request,
    ) -> None:
        """Логирует создание/редактирование (валидация через SelectField встроена в choices)."""
        logger.info(
            "SQLAdmin: %s PortalManagerSpecialist manager_sub=%s specialist_sub=%s",
            "создание" if is_created else "редактирование",
            data.get("manager_sub", ""),
            data.get("specialist_sub", ""),
        )
