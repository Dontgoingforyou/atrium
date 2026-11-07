"""Bulk-переиндексация эмбеддингов по типам сущностей."""

from __future__ import annotations

import logging
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.portal_search_constants import (
    PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT,
    PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT,
    PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE,
    PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
    PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
    PORTAL_SEARCH_ENTITY_TYPE_TASK,
)
from app.portal_search.services import entity_text as txt
from app.portal_search.services._embedding_chunk import iter_select_chunks, upsert_embedding_rows
from app.portal_search.services._embedding_specialists import (
    bulk_reindex_specialist_notes,
    bulk_reindex_specialists,
)

logger = logging.getLogger(__name__)


async def bulk_reindex_documents(db: AsyncSession) -> int:
    """Полная переиндексация активных документов (без корзины)."""
    count = 0
    async for rows in iter_select_chunks(
        db, "SELECT id, title, body, author_sub FROM portal_document WHERE deleted_at IS NULL"
    ):
        count += await upsert_embedding_rows(
            db,
            PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
            [str(row.id) for row in rows],
            [txt.document_to_text(r.title, r.body) for r in rows],
            [txt.document_meta(author_sub=row.author_sub) for row in rows],
        )
    logger.info("Переиндексация документов: %d записей", count)
    return count


async def bulk_reindex_tasks(db: AsyncSession) -> int:
    """Полная переиндексация всех задач."""
    count = 0
    async for rows in iter_select_chunks(
        db, "SELECT id, title, description, creator_sub, assignee_sub, status FROM portal_task"
    ):
        count += await upsert_embedding_rows(
            db,
            PORTAL_SEARCH_ENTITY_TYPE_TASK,
            [str(row.id) for row in rows],
            [txt.task_to_text(r.title, r.description) for r in rows],
            [
                txt.task_meta(creator_sub=row.creator_sub, assignee_sub=row.assignee_sub, status=row.status)
                for row in rows
            ],
        )
    logger.info("Переиндексация задач: %d записей", count)
    return count


async def bulk_reindex_chat_messages(db: AsyncSession) -> int:
    """Полная переиндексация сообщений DM и групповых инбокс-чатов (один батч-INSERT на чанк).

    Не индексируются чаты «только раздела» и не-DM без названия — как в полнотекстовом
    ``search_messages_for_user``.
    """
    count = 0
    async for rows in iter_select_chunks(
        db,
        "SELECT m.id, m.chat_id, m.body, m.author_sub "
        "FROM portal_chat_message m "
        "INNER JOIN portal_chat c ON c.id = m.chat_id "
        "WHERE m.deleted_for_all_at IS NULL "
        "AND m.body IS NOT NULL AND btrim(m.body) <> '' "
        "AND NOT ("
        "  c.canonical_dm_key IS NULL "
        "  AND (c.title IS NULL OR btrim(c.title) = '')"
        ")",
    ):
        count += await upsert_embedding_rows(
            db,
            PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE,
            [str(row.id) for row in rows],
            [txt.chat_message_to_text(r.body) for r in rows],
            [txt.chat_message_meta(chat_id=str(row.chat_id), author_sub=row.author_sub) for row in rows],
        )
    logger.info("Переиндексация сообщений: %d записей", count)
    return count


async def bulk_reindex_agreements(db: AsyncSession) -> int:
    """Полная переиндексация договорённостей."""
    count = 0
    async for rows in iter_select_chunks(db, "SELECT id, body, created_by_sub, status FROM portal_agreement"):
        count += await upsert_embedding_rows(
            db,
            PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT,
            [str(row.id) for row in rows],
            [txt.agreement_to_text(r.body) for r in rows],
            [txt.agreement_meta(created_by_sub=row.created_by_sub, status=row.status) for row in rows],
        )
    logger.info("Переиндексация договорённостей: %d записей", count)
    return count


async def bulk_reindex_learning_materials(db: AsyncSession) -> int:
    """Полная переиндексация учебных материалов."""
    count = 0
    async for rows in iter_select_chunks(
        db, "SELECT id, title, body, created_by_sub, status, material_type FROM portal_learning_material"
    ):
        count += await upsert_embedding_rows(
            db,
            PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL,
            [str(row.id) for row in rows],
            [txt.learning_material_to_text(r.title, r.body) for r in rows],
            [
                txt.learning_material_meta(
                    created_by_sub=row.created_by_sub,
                    status=row.status,
                    material_type=row.material_type,
                )
                for row in rows
            ],
        )
    logger.info("Переиндексация учебных материалов: %d записей", count)
    return count


async def bulk_reindex_calendar_events(db: AsyncSession) -> int:
    """Полная переиндексация событий календаря (без RBAC — фильтр при запросе)."""
    count = 0
    async for rows in iter_select_chunks(
        db,
        "SELECT id, calendar_id, title, description, location, organizer_sub FROM portal_calendar_event",
    ):
        count += await upsert_embedding_rows(
            db,
            PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT,
            [str(row.id) for row in rows],
            [txt.calendar_event_to_text(r.title, r.description, r.location) for r in rows],
            [
                txt.calendar_event_meta(calendar_id=str(row.calendar_id), organizer_sub=row.organizer_sub)
                for row in rows
            ],
        )
    logger.info("Переиндексация событий календаря: %d записей", count)
    return count


_REINDEX_HANDLERS: dict[str, Any] = {
    PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT: bulk_reindex_documents,
    PORTAL_SEARCH_ENTITY_TYPE_TASK: bulk_reindex_tasks,
    PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE: bulk_reindex_chat_messages,
    PORTAL_SEARCH_ENTITY_TYPE_AGREEMENT: bulk_reindex_agreements,
    PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL: bulk_reindex_learning_materials,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST: bulk_reindex_specialists,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE: bulk_reindex_specialist_notes,
    PORTAL_SEARCH_ENTITY_TYPE_CALENDAR_EVENT: bulk_reindex_calendar_events,
}


async def bulk_reindex(db: AsyncSession, entity_types: list[str] | None = None) -> dict[str, int]:
    """Переиндексирует все (или указанные) типы сущностей.

    Возвращает словарь {entity_type: количество_проиндексированных}.
    """
    start = time.monotonic()
    targets = entity_types or list(_REINDEX_HANDLERS.keys())
    totals: dict[str, int] = {}

    for et in targets:
        handler = _REINDEX_HANDLERS.get(et)
        if handler is None:
            logger.warning("Неизвестный тип сущности для переиндексации: %s", et)
            continue
        try:
            count = await handler(db)
            totals[et] = count
        except Exception:
            logger.exception("Ошибка переиндексации %s", et)
            totals[et] = -1

    elapsed = time.monotonic() - start
    logger.info("Bulk reindex завершён за %.2f с: %s", elapsed, totals)
    return totals
