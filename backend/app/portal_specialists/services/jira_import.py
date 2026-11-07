"""Импорт и привязка специалистов к Jira."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError, ServiceUnavailableError, ValidationError
from app.core.portal_search_constants import PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST
from app.core.utils import now_utc
from app.infrastructure.cache.rate_limit import enforce_rate_limit
from app.infrastructure.cache.token_cache import get_redis_client
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.integrations.jira.client import JiraClient
from app.integrations.jira.fields import (
    CF_BIRTHDATE,
    CF_CITY,
    CF_DIRECTION,
    CF_TELEGRAM,
    issue_key_regex,
)
from app.integrations.jira.jql import escape_jql_text
from app.integrations.jira.normalize import (
    extract_jira_field_text,
    extract_link_urls,
    normalize_issue_fields,
    parse_jira_date,
)
from app.portal_search.services.embedding import upsert_embedding_bg
from app.portal_search.services.entity_text import specialist_meta, specialist_to_text
from app.portal_specialists.services.board_realtime import publish_specialist_board_event
from app.portal_specialists.services.board_shared import (
    ensure_specialist_card_visible,
    require_specialist_write_access,
)
from app.portal_specialists.services.board_shared import (
    require_manager_or_admin as _require_manager_or_admin_read,
)
from app.portal_specialists.services.jira_board_sync import ensure_specialist_columns_from_jira
from app.portal_specialists.services.jira_import_board import (
    JIRA_IMPORTED_LINKS_KEY,
    JIRA_SYNCED_STATUS_ID_KEY,
    column_sync_needed,
    delete_imported_links,
    imported_link_pairs,
    resolve_column_key,
    stored_status_id,
    sync_column_for_specialist,
    upsert_imported_links,
)
from app.portal_specialists.services.sso_profile_normalize import (
    normalize_telegram_from_sso,
    parse_birthday_from_sso,
)
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

_JIRA_FORBIDDEN_MESSAGE = "Доступ к Jira — только для менеджера или администратора"


def _require_jira(settings: Settings) -> None:
    if not settings.jira_enabled:
        raise ServiceUnavailableError("Интеграция с Jira не настроена")


def _validate_issue_key(issue_key: str, project_key: str | None = None) -> str:
    settings = get_settings()
    pk = (project_key or settings.jira_project_key).strip().upper() or "BASE"
    key = issue_key.strip().upper()
    if not re.compile(issue_key_regex(pk)).match(key):
        raise ValidationError(f"Некорректный ключ задачи Jira (ожидается {pk}-123)")
    return key


async def search_jira_specialists(
    user: UserPublic,
    http: httpx.AsyncClient,
    q: str,
) -> list[dict[str, str]]:
    """Поиск карточек в Jira по summary."""
    _require_manager_or_admin_read(user, _JIRA_FORBIDDEN_MESSAGE)
    settings = get_settings()
    _require_jira(settings)

    query = q.strip()
    if len(query) < 2:
        raise ValidationError("Запрос поиска — минимум 2 символа")

    await enforce_rate_limit(
        f"jira:search:{user.sub}",
        limit=settings.jira_search_rate_limit,
        window_seconds=settings.jira_search_rate_window_seconds,
        message="Слишком много поисковых запросов к Jira",
    )

    escaped = escape_jql_text(query)
    project = escape_jql_text(settings.jira_project_key)
    jql = f'project = "{project}" AND summary ~ "{escaped}*"'
    client = JiraClient(settings, http)
    data = await client.search_issues(jql, fields=["summary", "status"], max_results=20)
    issues = data.get("issues") or []
    return [
        {
            "issue_key": str(item.get("key") or ""),
            "summary": str((item.get("fields") or {}).get("summary") or ""),
            "status_name": str(((item.get("fields") or {}).get("status") or {}).get("name") or ""),
        }
        for item in issues
        if item.get("key")
    ]


async def _refresh_specialist_embedding(
    session: AsyncSession,
    profile: PortalSpecialistProfile,
) -> None:
    user_profile = await session.get(PortalUserProfile, profile.specialist_sub)
    if user_profile is None:
        return
    await upsert_embedding_bg(
        PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
        profile.specialist_sub,
        specialist_to_text(
            user_profile.full_name,
            user_profile.email,
            profile.location,
            profile.telegram,
        ),
        specialist_meta(profile.specialist_sub),
    )


async def apply_jira_import(
    session: AsyncSession,
    *,
    specialist_sub: str,
    issue: dict[str, Any],
    actor_sub: str | None = None,
    http: httpx.AsyncClient | None = None,
) -> PortalSpecialistProfile:
    """Применить данные Jira issue к профилю специалиста (общая логика link/sync/webhook)."""
    fields_raw: dict[str, Any] = issue.get("fields") or {}
    profile = await session.get(PortalSpecialistProfile, specialist_sub)
    if profile is None:
        profile = PortalSpecialistProfile(specialist_sub=specialist_sub)
        session.add(profile)

    previously_linked = bool(profile.jira_issue_key)
    previous_status_id = stored_status_id(profile.jira_fields)
    status_obj = fields_raw.get("status") or {}
    new_status_id = str(status_obj.get("id") or "").strip() or None

    profile.jira_issue_key = str(issue.get("key") or profile.jira_issue_key)
    profile.jira_synced_at = now_utc()
    snapshot = normalize_issue_fields(issue)
    links = extract_link_urls(fields_raw)
    snapshot[JIRA_IMPORTED_LINKS_KEY] = [{"title": title, "url": url} for title, url in links]
    snapshot[JIRA_SYNCED_STATUS_ID_KEY] = new_status_id or ""
    profile.jira_fields = snapshot

    city = extract_jira_field_text(CF_CITY, fields_raw.get(CF_CITY))
    if city:
        profile.location = city

    telegram_raw = extract_jira_field_text(CF_TELEGRAM, fields_raw.get(CF_TELEGRAM))
    if telegram_raw:
        profile.telegram = normalize_telegram_from_sso(telegram_raw)

    birth_raw = fields_raw.get(CF_BIRTHDATE)
    if isinstance(birth_raw, str) and birth_raw.strip() and profile.birthdate is None:
        profile.birthdate = parse_birthday_from_sso(birth_raw) or parse_jira_date(birth_raw)

    direction_title = extract_jira_field_text(CF_DIRECTION, fields_raw.get(CF_DIRECTION))
    if direction_title:
        profile.direction = direction_title

    if http is not None:
        try:
            await ensure_specialist_columns_from_jira(session, http)
            await session.flush()
        except Exception:
            logger.warning("Jira import: не удалось подтянуть колонки доски", exc_info=True)

    if column_sync_needed(
        previously_linked=previously_linked,
        previous_status_id=previous_status_id,
        new_status_id=new_status_id,
    ):
        column_key = await resolve_column_key(
            session,
            new_status_id,
            str(status_obj.get("name") or "") or None,
        )
        await sync_column_for_specialist(session, specialist_sub, column_key)

    await upsert_imported_links(session, specialist_sub, actor_sub or specialist_sub, links)

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Задача уже привязана к другому специалисту") from exc
    await session.refresh(profile)
    await _refresh_specialist_embedding(session, profile)

    await publish_specialist_board_event(
        "specialist_jira_synced",
        specialist_sub=specialist_sub,
        actor_sub=actor_sub or "jira",
    )
    return profile


async def get_specialist_jira_state(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
) -> PortalSpecialistProfile:
    _require_manager_or_admin_read(user, _JIRA_FORBIDDEN_MESSAGE)
    user_profile = await session.get(PortalUserProfile, specialist_sub)
    if user_profile is None:
        raise NotFoundError("Пользователь не найден")
    await ensure_specialist_card_visible(session, user_profile)
    profile = await session.get(PortalSpecialistProfile, specialist_sub)
    if profile is None:
        return PortalSpecialistProfile(specialist_sub=specialist_sub)
    return profile


async def link_specialist_to_jira(
    session: AsyncSession,
    user: UserPublic,
    http: httpx.AsyncClient,
    specialist_sub: str,
    issue_key: str,
) -> PortalSpecialistProfile:
    _require_manager_or_admin_read(user, _JIRA_FORBIDDEN_MESSAGE)
    await require_specialist_write_access(session, user, specialist_sub)
    settings = get_settings()
    _require_jira(settings)
    key = _validate_issue_key(issue_key)

    other = (
        await session.execute(
            select(PortalSpecialistProfile).where(
                PortalSpecialistProfile.jira_issue_key == key,
                PortalSpecialistProfile.specialist_sub != specialist_sub,
            ),
        )
    ).scalar_one_or_none()
    if other is not None:
        raise ConflictError(f"Задача {key} уже привязана к другому специалисту")

    client = JiraClient(settings, http)
    issue = await client.get_issue(key)
    project_key = ((issue.get("fields") or {}).get("project") or {}).get("key")
    if project_key != settings.jira_project_key:
        raise ValidationError(f"Задача не из проекта {settings.jira_project_key}")

    return await apply_jira_import(session, specialist_sub=specialist_sub, issue=issue, actor_sub=user.sub, http=http)


async def sync_specialist_from_jira(
    session: AsyncSession,
    user: UserPublic,
    http: httpx.AsyncClient,
    specialist_sub: str,
) -> PortalSpecialistProfile:
    _require_manager_or_admin_read(user, _JIRA_FORBIDDEN_MESSAGE)
    await require_specialist_write_access(session, user, specialist_sub)
    settings = get_settings()
    _require_jira(settings)

    profile = await session.get(PortalSpecialistProfile, specialist_sub)
    if profile is None or not profile.jira_issue_key:
        raise NotFoundError("Специалист не привязан к Jira")

    client = JiraClient(settings, http)
    issue = await client.get_issue(profile.jira_issue_key)
    return await apply_jira_import(session, specialist_sub=specialist_sub, issue=issue, actor_sub=user.sub, http=http)


async def unlink_specialist_from_jira(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
) -> None:
    _require_manager_or_admin_read(user, _JIRA_FORBIDDEN_MESSAGE)
    await require_specialist_write_access(session, user, specialist_sub)

    profile = await session.get(PortalSpecialistProfile, specialist_sub)
    if profile is None:
        raise NotFoundError("Профиль специалиста не найден")

    imported = imported_link_pairs(profile.jira_fields)
    await delete_imported_links(session, specialist_sub, imported)
    profile.jira_issue_key = None
    profile.jira_synced_at = None
    profile.jira_fields = {}
    await session.commit()
    await publish_specialist_board_event(
        "specialist_jira_unlinked",
        specialist_sub=specialist_sub,
        actor_sub=user.sub,
    )


async def apply_jira_webhook(
    session: AsyncSession,
    http: httpx.AsyncClient,
    issue_key: str,
) -> bool:
    """Webhook: обновить привязанного специалиста. True если обновлено."""
    settings = get_settings()
    _require_jira(settings)
    key = _validate_issue_key(issue_key)

    redis = get_redis_client()
    debounce_key: str | None = None
    if redis is not None:
        debounce_key = f"jira:webhook:debounce:{key}"
        try:
            ok = await redis.set(debounce_key, "1", nx=True, ex=settings.jira_webhook_debounce_seconds)
            if not ok:
                return False
        except Exception as exc:
            logger.debug("Jira webhook debounce skip: %s", exc)
            debounce_key = None

    try:
        profile = (
            await session.execute(
                select(PortalSpecialistProfile).where(PortalSpecialistProfile.jira_issue_key == key),
            )
        ).scalar_one_or_none()
        if profile is None:
            return False

        client = JiraClient(settings, http)
        issue = await client.get_issue(key)
        await apply_jira_import(session, specialist_sub=profile.specialist_sub, issue=issue, actor_sub=None, http=http)
        return True
    except Exception:
        if redis is not None and debounce_key is not None:
            try:
                await redis.delete(debounce_key)
            except Exception as exc:
                logger.debug("Jira webhook debounce release skip: %s", exc)
        raise
