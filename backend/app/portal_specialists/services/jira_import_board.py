"""Колонка доски и ссылки, которые импорт Jira записывает специалисту."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_specialist_link import PortalSpecialistLink
from app.portal_specialists.services.specialist_jira_status_map import resolve_column_key_by_jira_status_id

JIRA_SYNCED_STATUS_ID_KEY = "synced_status_id"
JIRA_IMPORTED_LINKS_KEY = "imported_links"


def stored_status_id(fields: dict[str, Any] | None) -> str | None:
    raw = (fields or {}).get(JIRA_SYNCED_STATUS_ID_KEY)
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def column_sync_needed(
    *,
    previously_linked: bool,
    previous_status_id: str | None,
    new_status_id: str | None,
) -> bool:
    """Колонку двигает первая привязка и смена id статуса, не любой вебхук."""
    if not previously_linked:
        return True
    if not previous_status_id or not new_status_id:
        return False
    return previous_status_id != new_status_id


async def resolve_column_key(session: AsyncSession, status_id: str | None, status_name: str | None) -> str | None:
    if status_id:
        mapped_key = await resolve_column_key_by_jira_status_id(session, status_id)
        if mapped_key is not None:
            return mapped_key
        col = (
            await session.execute(
                select(PortalSpecialistColumn).where(PortalSpecialistColumn.jira_status_id == status_id),
            )
        ).scalar_one_or_none()
        if col is not None:
            return col.key
    if status_name:
        col = (
            await session.execute(
                select(PortalSpecialistColumn).where(
                    func.lower(PortalSpecialistColumn.title) == status_name.strip().lower(),
                ),
            )
        ).scalar_one_or_none()
        if col is not None:
            return col.key
    return None


async def sync_column_for_specialist(session: AsyncSession, specialist_sub: str, column_key: str | None) -> None:
    if not column_key:
        return
    stmt = select(PortalManagerSpecialist).where(PortalManagerSpecialist.specialist_sub == specialist_sub)
    for row in (await session.execute(stmt)).scalars():
        row.column_key = column_key


async def upsert_imported_links(
    session: AsyncSession,
    specialist_sub: str,
    actor_sub: str,
    links: list[tuple[str, str]],
) -> None:
    if not links:
        return
    existing = list(
        (
            await session.execute(
                select(PortalSpecialistLink).where(PortalSpecialistLink.specialist_sub == specialist_sub),
            )
        )
        .scalars()
        .all()
    )
    by_title = {link.title: link for link in existing}
    for title, url in links:
        link = by_title.get(title)
        if link is None:
            session.add(
                PortalSpecialistLink(
                    specialist_sub=specialist_sub,
                    title=title,
                    url=url,
                    created_by_sub=actor_sub,
                ),
            )
        else:
            link.url = url


def imported_link_pairs(fields: dict[str, Any] | None) -> list[tuple[str, str]]:
    raw = (fields or {}).get(JIRA_IMPORTED_LINKS_KEY) or []
    if not isinstance(raw, list):
        return []
    out: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        if title and url:
            out.append((title, url))
    return out


async def delete_imported_links(
    session: AsyncSession,
    specialist_sub: str,
    imported: list[tuple[str, str]],
) -> None:
    """Удалить только ссылки последнего Jira import; ручные не трогать."""
    if not imported:
        return
    imported_set = set(imported)
    existing = list(
        (
            await session.execute(
                select(PortalSpecialistLink).where(PortalSpecialistLink.specialist_sub == specialist_sub),
            )
        )
        .scalars()
        .all()
    )
    for link in existing:
        if (link.title, link.url) in imported_set:
            await session.delete(link)
