"""Оркестрация полнотекстового и семантического поиска.

Единственный слой, координирующий вызовы отдельных поисковых сервисов
и сборку списка результатов. Роутер остаётся чистым HTTP-слоем.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, ForbiddenError, ServiceUnavailableError
from app.core.portal_search_constants import (
    PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT,
    PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE,
    PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
    PORTAL_SEARCH_ENTITY_TYPE_TASK,
    PORTAL_SEARCH_ENTITY_TYPES,
)
from app.portal_calendar.remote import CalendarRemote, remote_event_search_query_fits
from app.portal_calendar.services import search_events as calendar_search_events
from app.portal_chat.services import chat as chat_svc
from app.portal_collab.services import task as task_svc
from app.portal_documents.services import portal_document as doc_svc
from app.portal_search.schemas.search import (
    PortalSearchHitResponseUnion,
    PortalSemanticHit,
    PortalSemanticSearchResponse,
)
from app.portal_search.services import search as search_svc
from app.portal_search.services import search_filters as search_filter_svc
from app.portal_search.services._search_format import (
    calendar_event_search_hit,
    chat_message_search_hit,
    document_search_hit,
    nav_slug_map_for_documents,
    specialist_search_hit,
    task_search_hit,
)
from app.portal_search.services._search_merge import (
    fulltext_hit_to_lexical_dict,
    merge_lexical_first,
)
from app.portal_specialists.services import search as specialist_search_svc
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)


async def _search_specialists_or_empty(
    db: AsyncSession,
    user: UserPublic,
    qt: str,
    *,
    status_ids: list[uuid.UUID] | None,
    skip: int,
    limit: int,
) -> list[Any]:
    """Специалисты видны только менеджерам/portal_admin — при отказе деградировать до пустого списка.

    Не роняет весь мультитиповой (или одиночный) глобальный поиск целиком из-за отсутствия
    прав на один конкретный тип; отказ доступа — ожидаемая ситуация, логируется как аудит-след
   , а не проглатывается тихо.
    """
    try:
        return await specialist_search_svc.search_specialists_for_user(
            db, user, qt, status_ids=status_ids, skip=skip, limit=limit
        )
    except ForbiddenError:
        logger.warning("Отказ в доступе к поиску специалистов: user_sub=%s", user.sub)
        return []


async def _calendar_hits(
    db: AsyncSession,
    user: UserPublic,
    qt: str,
    *,
    skip: int,
    limit: int,
    calendar_remote: CalendarRemote | None,
    omit_calendar: bool = False,
) -> list[Any]:
    if omit_calendar:
        return []
    if calendar_remote is not None:
        if not remote_event_search_query_fits(qt):
            return []
        try:
            remote_hits, _total = await calendar_remote.search_events(qt, skip, limit)
        except AppError:
            logger.warning("Поиск событий календаря недоступен: user_sub=%s", user.sub)
            return []
        return list(remote_hits)
    local_hits, _total = await calendar_search_events(db, user, qt, skip=skip, limit=limit)
    return list(local_hits)


async def run_fulltext_search(
    db: AsyncSession,
    user: UserPublic,
    qt: str,
    resolved_types: list[str],
    *,
    tag_slug: list[str] | None,
    status_ids: list[uuid.UUID] | None,
    skip: int,
    limit: int,
    calendar_remote: CalendarRemote | None = None,
    omit_calendar: bool = False,
) -> list[PortalSearchHitResponseUnion]:
    """Выполнить полнотекстовый поиск по одному или нескольким типам сущностей.

    Договорённости (``agreement``) сознательно не входят в глобальный полнотекстовый поиск
    (см. README пакета) — тип отсекается валидацией в роутере до вызова этой функции.

    При одном типе — пагинация передаётся напрямую в сервис (быстрый путь).
    При нескольких — merge_cap + merge_and_slice.
    """
    if len(resolved_types) == 1:
        return await _single_type_search(
            db,
            user,
            qt,
            resolved_types[0],
            tag_slug=tag_slug,
            status_ids=status_ids,
            skip=skip,
            limit=limit,
            calendar_remote=calendar_remote,
            omit_calendar=omit_calendar,
        )

    cap = search_svc.merge_cap(skip, limit)
    doc_stream: list[tuple[datetime, Any]] = []
    msg_stream: list[tuple[datetime, Any]] = []
    task_stream: list[tuple[datetime, Any]] = []
    specialist_stream: list[tuple[datetime, Any]] = []
    calendar_stream: list[tuple[datetime, Any]] = []

    if PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT in resolved_types:
        document_ids = await doc_svc.readable_document_ids_for_user(db, user)
        docs = await doc_svc.search_documents(db, qt, tag_slugs=tag_slug, document_ids=document_ids, skip=0, limit=cap)
        slug_map = await nav_slug_map_for_documents(db, {d.id for d in docs})
        for d in docs:
            doc_stream.append((d.created_at, document_search_hit(d, slug_map)))

    if PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE in resolved_types:
        for m, ch in await chat_svc.search_messages_for_user(db, user, qt, skip=0, limit=cap):
            msg_stream.append((m.created_at, chat_message_search_hit(m, ch)))

    if PORTAL_SEARCH_ENTITY_TYPE_TASK in resolved_types:
        for t in await task_svc.search_tasks_for_user(db, user, qt, skip=0, limit=cap):
            task_stream.append((t.created_at, task_search_hit(t)))

    if PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST in resolved_types:
        for s in await _search_specialists_or_empty(db, user, qt, status_ids=status_ids, skip=0, limit=cap):
            specialist_stream.append((s.created_at, specialist_search_hit(s)))

    if PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT in resolved_types:
        cal_hits = await _calendar_hits(
            db, user, qt, skip=0, limit=cap, calendar_remote=calendar_remote, omit_calendar=omit_calendar
        )
        for h in cal_hits:
            calendar_stream.append((h.starts_at, calendar_event_search_hit(h)))

    return search_svc.merge_and_slice(
        doc_stream, msg_stream, task_stream, specialist_stream, calendar_stream, skip=skip, limit=limit
    )


async def _single_type_search(
    db: AsyncSession,
    user: UserPublic,
    qt: str,
    entity_type: str,
    *,
    tag_slug: list[str] | None,
    status_ids: list[uuid.UUID] | None,
    skip: int,
    limit: int,
    calendar_remote: CalendarRemote | None = None,
    omit_calendar: bool = False,
) -> list[PortalSearchHitResponseUnion]:
    if entity_type == PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT:
        document_ids = await doc_svc.readable_document_ids_for_user(db, user)
        docs = await doc_svc.search_documents(
            db, qt, tag_slugs=tag_slug, document_ids=document_ids, skip=skip, limit=limit
        )
        slug_map = await nav_slug_map_for_documents(db, {d.id for d in docs})
        return [document_search_hit(d, slug_map) for d in docs]

    if entity_type == PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE:
        rows = await chat_svc.search_messages_for_user(db, user, qt, skip=skip, limit=limit)
        return [chat_message_search_hit(m, ch) for m, ch in rows]

    if entity_type == PORTAL_SEARCH_ENTITY_TYPE_TASK:
        tasks = await task_svc.search_tasks_for_user(db, user, qt, skip=skip, limit=limit)
        return [task_search_hit(t) for t in tasks]

    if entity_type == PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST:
        specialists = await _search_specialists_or_empty(db, user, qt, status_ids=status_ids, skip=skip, limit=limit)
        return [specialist_search_hit(s) for s in specialists]

    if entity_type == PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT:
        hits = await _calendar_hits(
            db, user, qt, skip=skip, limit=limit, calendar_remote=calendar_remote, omit_calendar=omit_calendar
        )
        return [calendar_event_search_hit(h) for h in hits]

    return []


async def _lexical_dicts_for_semantic(
    db: AsyncSession,
    user: UserPublic,
    qt: str,
    resolved_types: list[str],
    *,
    tag_slug: list[str] | None,
    status_ids: list[uuid.UUID] | None,
    skip: int,
    limit: int,
    calendar_remote: CalendarRemote | None = None,
    omit_calendar: bool = False,
) -> list[dict[str, Any]]:
    """Полнотекст по тем же типам, что умеет GET /portal/search — слово из запроса не теряем."""
    lexical_types = [t for t in resolved_types if t in PORTAL_SEARCH_ENTITY_TYPES]
    if not lexical_types:
        return []
    ft_hits = await run_fulltext_search(
        db,
        user,
        qt,
        lexical_types,
        tag_slug=tag_slug,
        status_ids=status_ids,
        skip=0,
        limit=max(skip + limit, 1),
        calendar_remote=calendar_remote,
        omit_calendar=omit_calendar,
    )
    out: list[dict[str, Any]] = []
    for hit in ft_hits:
        row = fulltext_hit_to_lexical_dict(hit)
        if row is not None:
            out.append(row)
    return out


async def run_semantic_search(
    db: AsyncSession,
    user: UserPublic,
    qt: str,
    resolved_types: list[str],
    *,
    tag_slug: list[str] | None,
    status_ids: list[uuid.UUID] | None,
    skip: int,
    limit: int,
    min_score: float,
    calendar_remote: CalendarRemote | None = None,
    omit_calendar: bool = False,
) -> PortalSemanticSearchResponse:
    """Семантика (pgvector) плюс полнотекст: точное слово не тонет за косинусом."""
    from app.portal_search.services import embedding as emb_svc  # noqa: PLC0415

    settings = get_settings()
    has_calendar = PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT in resolved_types
    document_ids = await doc_svc.readable_document_ids_for_user(db, user)
    has_doc_rbac = document_ids is not None
    has_post_filters = bool((tag_slug and len(tag_slug) > 0) or status_ids or has_calendar or has_doc_rbac)
    top_k = min(settings.semantic_search_top_k, skip + limit)
    if has_post_filters:
        top_k = min(settings.semantic_search_top_k, min(500, max(top_k * 5, 50)))

    try:
        query_embedding = await emb_svc.generate_embedding(qt)
    except Exception:
        logger.exception("Семантический поиск: ошибка генерации эмбеддинга")
        raise ServiceUnavailableError("Семантический поиск временно недоступен") from None

    try:
        raw_hits = await search_svc.semantic_search(
            db=db,
            query_embedding=query_embedding,
            entity_types=resolved_types,
            top_k=top_k,
            min_score=min_score,
            user=user,
        )
    except Exception:
        logger.exception("Семантический поиск: ошибка запроса к индексу pgvector")
        raise ServiceUnavailableError("Семантический поиск временно недоступен") from None
    if omit_calendar:
        raw_hits = [hit for hit in raw_hits if hit.get("entity_type") != PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT]
    filtered_hits = await search_filter_svc.filter_semantic_hits(
        db,
        raw_hits,
        tag_slugs=tag_slug,
        status_ids=status_ids,
        viewer_user=user if has_calendar else None,
        allowed_document_ids=document_ids,
        calendar_remote=calendar_remote,
    )
    # Полнотекст уже применил те же RBAC/теги/статусы — второй filter не нужен.
    lexical_hits = await _lexical_dicts_for_semantic(
        db,
        user,
        qt,
        resolved_types,
        tag_slug=tag_slug,
        status_ids=status_ids,
        skip=skip,
        limit=limit,
        calendar_remote=calendar_remote,
        omit_calendar=omit_calendar,
    )
    merged = merge_lexical_first(lexical_hits, filtered_hits)

    hits = merged[skip : skip + limit]
    results = [
        PortalSemanticHit(
            entity_type=h["entity_type"],
            entity_id=h["entity_id"],
            text_excerpt=str(h.get("text_content") or "")[:300],
            similarity_score=h.get("similarity_score"),
            meta=h["meta"] if isinstance(h.get("meta"), dict) else {},
        )
        for h in hits
    ]
    return PortalSemanticSearchResponse(query=qt, results=results, total_found=len(merged))
