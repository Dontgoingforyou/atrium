from __future__ import annotations

from typing import Any

from markupsafe import Markup
from sqladmin import ModelView
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from starlette.requests import Request

from app.admin.sqladmin_categories import SQLADMIN_CATEGORY_SPECIALISTS
from app.core.text_search import escape_ilike_pattern
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_specialists.admin.board import profile_display
from app.portal_specialists.services.sso_profile_normalize import normalize_telegram_from_sso
from app.services.portal_user_visibility import specialist_profile_directory_visible_sql


def _fmt_birthdate(model: PortalSpecialistProfile, _name: Any) -> str:
    return model.birthdate.isoformat() if model.birthdate else "—"


def _fmt_telegram(model: PortalSpecialistProfile, _name: Any) -> str | Markup:
    return _telegram_admin_markup(model.telegram)


def _telegram_admin_markup(raw: str | None) -> str | Markup:
    """Безопасная ссылка Telegram для SQLAdmin (только https://t.me/…)."""
    if not raw:
        return "—"
    url = normalize_telegram_from_sso(raw)
    if not url:
        return Markup.escape(raw)
    safe_url = Markup.escape(url)
    return Markup(f'<a href="{safe_url}" target="_blank" rel="noopener">{safe_url}</a>')


class PortalSpecialistProfileAdmin(ModelView, model=PortalSpecialistProfile):
    """Расширенный профиль специалиста: дата рождения, локация, Telegram."""

    name = "Сотрудник"
    name_plural = "Сотрудники"
    icon = "fa-solid fa-id-card"
    category = SQLADMIN_CATEGORY_SPECIALISTS

    column_list = [
        "user_profile",
        PortalSpecialistProfile.birthdate,
        PortalSpecialistProfile.location,
        PortalSpecialistProfile.telegram,
    ]
    column_details_list = [
        "user_profile",
        PortalSpecialistProfile.birthdate,
        PortalSpecialistProfile.location,
        PortalSpecialistProfile.telegram,
    ]
    column_sortable_list = [
        PortalSpecialistProfile.birthdate,
        PortalSpecialistProfile.location,
    ]
    column_default_sort = [(PortalSpecialistProfile.specialist_sub, False)]
    column_searchable_list = [
        "user_profile.full_name",
        "user_profile.email",
        PortalSpecialistProfile.location,
        PortalSpecialistProfile.telegram,
    ]
    column_labels = {
        "user_profile": "Сотрудник",
        "user_profile.full_name": "ФИО",
        "user_profile.email": "Email",
        "birthdate": "Дата рождения",
        "location": "Локация",
        "telegram": "Telegram",
    }
    column_formatters = {
        "user_profile": lambda m, a: profile_display(
            getattr(m, "user_profile", None), getattr(m, "specialist_sub", "")
        ),
        "birthdate": _fmt_birthdate,  # type: ignore[dict-item, unused-ignore]
        "telegram": _fmt_telegram,  # type: ignore[dict-item, unused-ignore]
    }
    column_formatters_detail = {
        "user_profile": lambda m, a: profile_display(
            getattr(m, "user_profile", None), getattr(m, "specialist_sub", "")
        ),
    }
    form_excluded_columns = [
        PortalSpecialistProfile.specialist_sub,
        "user_profile",
        PortalSpecialistProfile.direction,
        PortalSpecialistProfile.jira_issue_key,
        PortalSpecialistProfile.jira_synced_at,
        PortalSpecialistProfile.jira_fields,
        "version",
    ]
    form_args = {
        "birthdate": {"description": "Подтягивается из профиля, вручную не редактируется."},
        "telegram": {"description": "Подтягивается из профиля, вручную не редактируется."},
    }
    form_widget_args = {
        "birthdate": {"readonly": True},
        "telegram": {"readonly": True},
    }

    can_create = False
    can_edit = True
    can_delete = False
    can_view_details = True

    async def on_model_change(self, data: dict[str, Any], model: Any, is_created: bool, request: Request) -> None:
        from app.admin.cas_version import bump_cas_version_on_edit

        bump_cas_version_on_edit(data, model, is_created=is_created)

    def search_query(self, stmt: Any, term: str) -> Any:
        """ILIKE по ФИО/email связанного профиля, локации и Telegram; %/_ экранируются."""
        pattern = f"%{escape_ilike_pattern(term)}%"
        return stmt.join(
            PortalUserProfile,
            PortalSpecialistProfile.specialist_sub == PortalUserProfile.sub,
        ).where(
            or_(
                PortalUserProfile.full_name.ilike(pattern, escape="\\"),
                PortalUserProfile.email.ilike(pattern, escape="\\"),
                PortalSpecialistProfile.location.ilike(pattern, escape="\\"),
                PortalSpecialistProfile.telegram.ilike(pattern, escape="\\"),
            )
        )

    def list_query(self, request: Request) -> Any:
        return (
            select(PortalSpecialistProfile)
            .options(selectinload(PortalSpecialistProfile.user_profile))
            .where(specialist_profile_directory_visible_sql())
        )

    def details_query(self, request: Request) -> Any:
        return (
            select(PortalSpecialistProfile)
            .options(selectinload(PortalSpecialistProfile.user_profile))
            .where(specialist_profile_directory_visible_sql())
        )
