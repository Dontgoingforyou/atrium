from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.core.portal_search_constants import (
    PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT,
    PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
)
from app.infrastructure.db.models.portal_document import PortalDocumentTag, PortalTag
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist

logger = logging.getLogger(__name__)


def document_ids_for_tag_slugs_subquery(tag_slugs: list[str]) -> Any:
    """Подзапрос: document_id документов, помеченных хотя бы одним из тегов.

    Синхронный; используется как ``WHERE PortalDocument.id.in_(subquery)``
    внутри составных запросов, чтобы избежать лишнего JOIN к тегам.
    """
    return (
        select(PortalDocumentTag.document_id)
        .join(PortalTag, PortalTag.id == PortalDocumentTag.tag_id)
        .where(PortalTag.slug.in_(tag_slugs))
        .distinct()
    )


async def document_ids_for_tag_slugs(session: AsyncSession, tag_slugs: list[str]) -> set[uuid.UUID]:
    if not tag_slugs:
        return set()
    stmt = (
        select(PortalDocumentTag.document_id)
        .join(PortalTag, PortalTag.id == PortalDocumentTag.tag_id)
        .where(PortalTag.slug.in_(tag_slugs))
        .distinct()
    )
    return set((await session.scalars(stmt)).all())


async def specialist_subs_for_status_ids(
    session: AsyncSession,
    status_ids: list[uuid.UUID],
) -> set[str]:
    if not status_ids:
        return set()
    stmt = (
        select(PortalManagerSpecialist.specialist_sub)
        .where(PortalManagerSpecialist.status_id.in_(status_ids))
        .distinct()
    )
    return set((await session.scalars(stmt)).all())


def _specialist_sub_from_hit(hit: dict[str, Any]) -> str | None:
    meta = hit.get("meta") or {}
    if isinstance(meta, dict):
        sub = meta.get("specialist_sub")
        if sub:
            return str(sub)
    entity_id = hit.get("entity_id")
    return str(entity_id) if entity_id else None


async def filter_semantic_hits(
    session: AsyncSession,
    hits: list[dict[str, Any]],
    *,
    tag_slugs: list[str] | None,
    status_ids: list[uuid.UUID] | None,
    viewer_user: Any | None = None,
    allowed_document_ids: list[uuid.UUID] | None = None,
    calendar_remote: Any | None = None,
) -> list[dict[str, Any]]:
    """Сужает семантические hits по тегам документов, направлениям специалистов и RBAC календаря."""
    out = hits
    if allowed_document_ids is not None:
        allowed_docs = {str(d) for d in allowed_document_ids}
        out = [
            h
            for h in out
            if h.get("entity_type") != PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT or str(h.get("entity_id")) in allowed_docs
        ]
    if tag_slugs:
        doc_ids = await document_ids_for_tag_slugs(session, tag_slugs)
        allowed_docs = {str(d) for d in doc_ids}
        out = [
            h
            for h in out
            if h.get("entity_type") != PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT or str(h.get("entity_id")) in allowed_docs
        ]
    if status_ids:
        allowed_subs = await specialist_subs_for_status_ids(session, status_ids)
        out = [
            h
            for h in out
            if h.get("entity_type")
            not in (PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST, PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE)
            or (_specialist_sub_from_hit(h) in allowed_subs)
        ]
    if viewer_user is not None and any(h.get("entity_type") == PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT for h in out):
        if calendar_remote is not None:
            out = await _visible_calendar_hits(out, calendar_remote)
        else:
            from app.portal_calendar.services import accessible_calendar_event_ids

            cal_ids: list[uuid.UUID] = []
            for h in out:
                if h.get("entity_type") != PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT:
                    continue
                eid = _safe_uuid(h.get("entity_id"))
                if eid is not None:
                    cal_ids.append(eid)
            allowed_ids = await accessible_calendar_event_ids(session, viewer_user, cal_ids)
            filtered: list[dict[str, Any]] = []
            for h in out:
                if h.get("entity_type") != PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT:
                    filtered.append(h)
                    continue
                eid = _safe_uuid(h.get("entity_id"))
                if eid is not None and eid in allowed_ids:
                    filtered.append(h)
            out = filtered
    return out


async def _visible_calendar_hits(hits: list[dict[str, Any]], calendar_remote: Any) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for hit in hits:
        if hit.get("entity_type") != PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT:
            kept.append(hit)
            continue
        event_id = _safe_uuid(hit.get("entity_id"))
        if event_id is None:
            continue
        try:
            await calendar_remote.get_event(event_id)
        except AppError as exc:
            if exc.status_code in (403, 404):
                continue
            logger.warning("Семантический поиск: календарь недоступен")
            return [item for item in hits if item.get("entity_type") != PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT]
        kept.append(hit)
    return kept


def _safe_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None
