"""Синхронизация колонок воронки портала с доской Jira."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, ServiceUnavailableError
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.integrations.jira.client import JiraClient
from app.portal_specialists.services.specialist_jira_status_map import replace_status_maps_from_board_config
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

_DEFAULT_COLORS = (
    "#6366f1",
    "#8b5cf6",
    "#f59e0b",
    "#3b82f6",
    "#22c55e",
    "#ef4444",
    "#ec4899",
    "#14b8a6",
    "#f97316",
    "#64748b",
    "#a855f7",
)


def _column_key_from_name(name: str, position: int) -> str:
    base = slugify(name, separator="-", lowercase=True)
    if base:
        return base[:100]
    return f"jira-col-{position}"


async def upsert_columns_from_board_config(
    session: AsyncSession,
    board_config: dict[str, Any],
) -> list[PortalSpecialistColumn]:
    """Upsert колонок и status map из конфига доски Jira. Без commit."""
    columns_raw: list[dict[str, Any]] = (board_config.get("columnConfig") or {}).get("columns") or []
    existing = {col.key: col for col in (await session.execute(select(PortalSpecialistColumn))).scalars().all()}
    existing_by_title = {col.title.strip().lower(): col for col in existing.values()}

    result: list[PortalSpecialistColumn] = []
    for position, jira_col in enumerate(columns_raw):
        name = str(jira_col.get("name") or f"Колонка {position + 1}")
        title_key = name.strip().lower()
        statuses: list[dict[str, Any]] = jira_col.get("statuses") or []
        primary_status_id = str(statuses[0]["id"]) if statuses else None

        key = _column_key_from_name(name, position)
        col = existing_by_title.get(title_key)
        if col is None:
            if key in existing and existing[key].title.strip().lower() != title_key:
                key = f"{key}-{position}"
            col = existing.get(key)
        if col is None:
            col = PortalSpecialistColumn(
                id=uuid.uuid4(),
                key=key,
                title=name,
                color=_DEFAULT_COLORS[position % len(_DEFAULT_COLORS)],
                position=position,
                jira_status_id=primary_status_id,
            )
            session.add(col)
            existing[col.key] = col
            existing_by_title[title_key] = col
        else:
            col.title = name
            col.position = position
            col.jira_status_id = primary_status_id

        result.append(col)

    columns_by_title = {col.title.strip().lower(): col for col in result}
    await replace_status_maps_from_board_config(session, board_config, columns_by_title=columns_by_title)
    return result


async def ensure_specialist_columns_from_jira(
    session: AsyncSession,
    http: httpx.AsyncClient,
) -> list[PortalSpecialistColumn]:
    """Подтянуть колонки с доски Jira (без проверки admin, без commit)."""
    settings = get_settings()
    if not settings.jira_enabled:
        return []
    client = JiraClient(settings, http)
    config = await client.get_board_configuration()
    return await upsert_columns_from_board_config(session, config)


async def sync_columns_from_jira(
    session: AsyncSession,
    user: UserPublic,
    http: httpx.AsyncClient,
) -> list[PortalSpecialistColumn]:
    """Upsert колонок воронки из конфигурации доски Jira. Только portal_admin."""
    if not user.is_portal_admin:
        raise ForbiddenError("Синхронизация колонок из Jira — только для администратора портала")

    settings = get_settings()
    if not settings.jira_enabled:
        raise ServiceUnavailableError("Интеграция с Jira не настроена")

    try:
        result = await ensure_specialist_columns_from_jira(session, http)
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Конфликт колонок при синхронизации с Jira (дубликат ключа или статуса)") from exc
    for col in result:
        await session.refresh(col)

    logger.info(
        "Jira board sync: upsert %d columns user_sub=%s",
        len(result),
        user.sub,
    )
    return result
