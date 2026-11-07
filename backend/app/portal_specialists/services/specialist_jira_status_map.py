"""Маппинг всех status id колонок доски Jira → portal_specialist_column."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_specialist_jira_status_map import PortalSpecialistJiraStatusMap


def iter_jira_column_status_pairs(
    board_config: dict[str, Any],
) -> list[tuple[str, str]]:
    """(jira_status_id, jira_column_name) для каждого статуса на доске."""
    columns_raw: list[dict[str, Any]] = (board_config.get("columnConfig") or {}).get("columns") or []
    out: list[tuple[str, str]] = []
    for jira_col in columns_raw:
        name = str(jira_col.get("name") or "").strip()
        if not name:
            continue
        for st in jira_col.get("statuses") or []:
            sid = str(st.get("id") or "").strip()
            if sid:
                out.append((sid, name))
    return out


async def replace_status_maps_from_board_config(
    session: AsyncSession,
    board_config: dict[str, Any],
    *,
    columns_by_title: dict[str, PortalSpecialistColumn],
) -> int:
    """Пересобрать таблицу маппинга по конфигу доски Jira. Возвращает число записей."""
    await session.execute(delete(PortalSpecialistJiraStatusMap))
    count = 0
    for sid, jira_name in iter_jira_column_status_pairs(board_config):
        col = columns_by_title.get(jira_name.strip().lower())
        if col is None:
            continue
        session.add(PortalSpecialistJiraStatusMap(jira_status_id=sid, column_id=col.id))
        count += 1
    return count


async def resolve_column_key_by_jira_status_id(
    session: AsyncSession,
    status_id: str,
) -> str | None:
    row = (
        await session.execute(
            select(PortalSpecialistColumn.key)
            .join(
                PortalSpecialistJiraStatusMap,
                PortalSpecialistJiraStatusMap.column_id == PortalSpecialistColumn.id,
            )
            .where(PortalSpecialistJiraStatusMap.jira_status_id == status_id),
        )
    ).scalar_one_or_none()
    return row
