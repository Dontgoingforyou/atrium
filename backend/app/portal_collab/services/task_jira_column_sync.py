"""Привязка portal_task_column.jira_status_id к статусам доски TASKS."""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, ServiceUnavailableError
from app.infrastructure.db.models.portal_task import PortalTaskColumn
from app.integrations.jira.client import JiraClient
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

_TITLE_ALIASES_TO_JIRA: dict[str, str] = {
    "бэклог": "список задач",
    "готово": "выполнено",
}

_WS_RE = re.compile(r"\s+")


def normalize_column_title(title: str) -> str:
    """Нормализация для сопоставления: trim, схлопывание пробелов, casefold."""
    return _WS_RE.sub(" ", (title or "").strip()).casefold()


def resolve_jira_lookup_key(atrium_title: str) -> str:
    """Ключ поиска в индексе колонок Jira с учётом алиасов."""
    norm = normalize_column_title(atrium_title)
    return _TITLE_ALIASES_TO_JIRA.get(norm, norm)


def build_jira_status_index(board_config: dict[str, Any]) -> dict[str, str]:
    """name колонки доски (norm) → primary status id."""
    columns_raw: list[dict[str, Any]] = (board_config.get("columnConfig") or {}).get("columns") or []
    index: dict[str, str] = {}
    for jira_col in columns_raw:
        name = str(jira_col.get("name") or "")
        statuses: list[dict[str, Any]] = jira_col.get("statuses") or []
        if not name or not statuses:
            continue
        sid = statuses[0].get("id")
        if sid is None:
            continue
        index[normalize_column_title(name)] = str(sid)
    return index


def status_id_for_atrium_title(title: str, jira_by_name: dict[str, str]) -> str | None:
    key = resolve_jira_lookup_key(title)
    return jira_by_name.get(key)


async def fetch_tasks_board_status_index(http: httpx.AsyncClient) -> dict[str, str]:
    settings = get_settings()
    if not settings.jira_enabled:
        raise ServiceUnavailableError("Интеграция с Jira не настроена")
    client = JiraClient(settings, http)
    config = await client.get_board_configuration(settings.jira_tasks_board_id)
    return build_jira_status_index(config)


async def bind_column_jira_status_by_title(
    column: PortalTaskColumn,
    http: httpx.AsyncClient,
    *,
    jira_by_name: dict[str, str] | None = None,
) -> bool:
    """Проставить jira_status_id по title. True если найден match."""
    try:
        index = jira_by_name if jira_by_name is not None else await fetch_tasks_board_status_index(http)
    except ServiceUnavailableError:
        logger.warning("Jira column bind skipped: Jira недоступна title=%s", column.title)
        return False
    sid = status_id_for_atrium_title(column.title, index)
    if sid is None:
        return False
    column.jira_status_id = sid
    return True


async def sync_task_column_jira_status_ids(
    session: AsyncSession,
    user: UserPublic,
    http: httpx.AsyncClient,
) -> dict[str, Any]:
    """Привязать все колонки канбана к статусам доски TASKS. Только portal_admin."""
    if not user.is_portal_admin:
        raise ForbiddenError("Синхронизация маппинга колонок Jira — только для администратора портала")

    jira_by_name = await fetch_tasks_board_status_index(http)
    result = await session.execute(select(PortalTaskColumn).order_by(PortalTaskColumn.position))
    columns = list(result.scalars().all())

    bound = 0
    unbound_titles: list[str] = []
    matched_jira_keys: set[str] = set()

    for col in columns:
        sid = status_id_for_atrium_title(col.title, jira_by_name)
        if sid is None:
            unbound_titles.append(col.title)
            continue
        col.jira_status_id = sid
        bound += 1
        matched_jira_keys.add(resolve_jira_lookup_key(col.title))

    jira_only_titles = [name for name, _sid in sorted(jira_by_name.items()) if name not in matched_jira_keys]

    await session.commit()
    logger.info(
        "Task Jira column sync: bound=%s unbound=%s user_sub=%s",
        bound,
        len(unbound_titles),
        user.sub,
    )
    return {
        "bound": bound,
        "unbound_titles": unbound_titles,
        "jira_only_titles": jira_only_titles,
    }
