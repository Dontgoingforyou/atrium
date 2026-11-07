from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.portal_search_constants import (
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
    PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
)
from app.portal_search.services import entity_text as txt
from app.portal_search.services._embedding_chunk import iter_select_chunks, upsert_embedding_rows

logger = logging.getLogger(__name__)


async def bulk_reindex_specialists(db: AsyncSession) -> int:
    """Полная переиндексация профилей специалистов.

    Индексирует все записи portal_specialist_profile, объединённые
    с portal_user_profile для получения full_name и email.
    """
    count = 0
    async for rows in iter_select_chunks(
        db,
        "SELECT sp.specialist_sub, up.full_name, up.email, "
        "sp.location, sp.telegram "
        "FROM portal_specialist_profile sp "
        "JOIN portal_user_profile up ON up.sub = sp.specialist_sub",
    ):
        count += await upsert_embedding_rows(
            db,
            PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST,
            [row.specialist_sub for row in rows],
            [txt.specialist_to_text(r.full_name, r.email, r.location, r.telegram) for r in rows],
            [txt.specialist_meta(row.specialist_sub) for row in rows],
        )
    logger.info("Переиндексация специалистов: %d записей", count)
    return count


async def bulk_reindex_specialist_notes(db: AsyncSession) -> int:
    """Полная переиндексация заметок о специалистах."""
    count = 0
    async for rows in iter_select_chunks(db, "SELECT id, specialist_sub, author_sub, body FROM portal_specialist_note"):
        count += await upsert_embedding_rows(
            db,
            PORTAL_SEARCH_ENTITY_TYPE_SPECIALIST_NOTE,
            [str(row.id) for row in rows],
            [txt.specialist_note_to_text(r.body) for r in rows],
            [txt.specialist_note_meta(row.specialist_sub, row.author_sub) for row in rows],
        )
    logger.info("Переиндексация заметок специалистов: %d записей", count)
    return count
