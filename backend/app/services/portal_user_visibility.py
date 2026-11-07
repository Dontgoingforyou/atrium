"""Кто скрыт из пикеров людей и SQLAdmin «Сотрудники»."""

from __future__ import annotations

from collections.abc import Collection

import httpx
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.sql.elements import ColumnElement

from app.core.auth_constants import SSO_GID_OUTSTAFF
from app.core.config import get_settings
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.integrations.effective_admin.emails_check import EffectiveAdminEmailsClient, normalize_email
from app.services.ea_email_active_cache import get_cached_email_active_bulk, set_cached_email_active_bulk

# Явный список адресов, которые не показывать в пикерах. Учётки не удаляем.
HIDDEN_DIRECTORY_EMAILS: frozenset[str] = frozenset(
    {
        "hidden.one@example.com",
        "hidden.two@example.com",
        "hidden.three@example.com",
        "hidden.four@example.com",
        "hidden.five@example.com",
    }
)


def normalize_directory_email(email: str | None) -> str | None:
    if not email:
        return None
    normalized = normalize_email(email)
    return normalized or None


def is_hidden_test_account_email(email: str | None) -> bool:
    """Тестовые учётки: local-part вида ``test.…`` (test.managerau, test.outstaff)."""
    normalized = normalize_directory_email(email)
    if not normalized or "@" not in normalized:
        return False
    local = normalized.split("@", 1)[0]
    return local.startswith("test.")


def is_explicitly_hidden_directory_email(email: str | None) -> bool:
    """Явный список AUTASKS-413 или тестовая учётка — скрыть без сверки EA."""
    normalized = normalize_directory_email(email)
    if not normalized:
        return False
    return normalized in HIDDEN_DIRECTORY_EMAILS or is_hidden_test_account_email(normalized)


def directory_employee_visible_sql() -> ColumnElement[bool]:
    """SQL: не тестовый, не явный список, не чужой отдел (gid известен и не АУ)."""
    profile = PortalUserProfile
    email_norm = func.lower(func.trim(profile.email))
    hidden_by_email = and_(
        profile.email.is_not(None),
        or_(
            email_norm.like("test.%"),
            email_norm.in_(sorted(HIDDEN_DIRECTORY_EMAILS)),
        ),
    )
    hidden_by_dept = and_(
        profile.gid_number.is_not(None),
        profile.gid_number != SSO_GID_OUTSTAFF,
    )
    return and_(~hidden_by_email, ~hidden_by_dept)


def specialist_profile_directory_visible_sql() -> ColumnElement[bool]:
    """Строка SQLAdmin «Сотрудники» видна, если нет скрытого связанного профиля.

    ``select_from`` + ``correlate`` — иначе поиск SQLAdmin (JOIN профиля) вычищает
    FROM подзапроса автокорреляцией.
    """
    hidden_profile = exists(
        select(1)
        .select_from(PortalUserProfile)
        .where(
            PortalUserProfile.sub == PortalSpecialistProfile.specialist_sub,
            ~directory_employee_visible_sql(),
        )
        .correlate(PortalSpecialistProfile)
    )
    return ~hidden_profile


async def hidden_emails_for_directory(
    http: httpx.AsyncClient | None,
    emails: Collection[str | None],
) -> set[str]:
    """Почты, которые нельзя показывать в пикерах: тестовые, явный список и not_found в EA.

    Сбой или отсутствие сверки — не прячем «непроверенных» (fail-open), тестовые и явный список всё равно скрыты.
    """
    hidden: set[str] = set()
    to_check: list[str] = []
    seen: set[str] = set()
    for raw in emails:
        normalized = normalize_directory_email(raw)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        if is_explicitly_hidden_directory_email(normalized):
            hidden.add(normalized)
        else:
            to_check.append(normalized)

    if not to_check or http is None:
        return hidden
    settings = get_settings()
    if not settings.effective_admin_emails_check_enabled:
        return hidden

    cached = await get_cached_email_active_bulk(to_check)
    missing = [email for email in to_check if cached[email] is None]
    if missing:
        result = await EffectiveAdminEmailsClient(settings, http).check_emails(missing)
        if result is not None:
            fetched = {email: email in result.found for email in missing}
            await set_cached_email_active_bulk(fetched)
            cached.update(fetched)

    for email in to_check:
        if cached.get(email) is False:
            hidden.add(email)
    return hidden
