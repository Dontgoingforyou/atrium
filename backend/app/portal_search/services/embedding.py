"""Сервис хранения, переиндексации и фоновых задач для векторных эмбеддингов.

Генерация эмбеддингов через OpenAI API вынесена в `_embedding_generate.py`.
Bulk-переиндексация — в `_embedding_bulk_reindex.py`, фоновые обёртки — в `_embedding_background.py`.
"""

from __future__ import annotations

import json
import logging
import uuid

import sqlalchemy as sa
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.infrastructure.db.models.portal_embedding import PortalEmbedding
from app.portal_search.services._embedding_background import (
    bulk_reindex_bg,
    delete_embedding_bg,
    upsert_embedding_bg,
)
from app.portal_search.services._embedding_bulk_reindex import (
    _REINDEX_HANDLERS,
    bulk_reindex,
    bulk_reindex_agreements,
    bulk_reindex_calendar_events,
    bulk_reindex_chat_messages,
    bulk_reindex_documents,
    bulk_reindex_learning_materials,
    bulk_reindex_tasks,
)
from app.portal_search.services._embedding_generate import (
    coerce_embedding_dimension,
    generate_embedding,
    generate_embeddings_batch,
)
from app.portal_search.services._embedding_sql import UPSERT_EMBEDDING_SQL, vec_literal

logger = logging.getLogger(__name__)

__all__ = [
    "_REINDEX_HANDLERS",
    "bulk_reindex",
    "bulk_reindex_agreements",
    "bulk_reindex_bg",
    "bulk_reindex_calendar_events",
    "bulk_reindex_chat_messages",
    "bulk_reindex_documents",
    "bulk_reindex_learning_materials",
    "bulk_reindex_tasks",
    "delete_embedding",
    "delete_embedding_bg",
    "delete_embeddings_batch",
    "delete_embeddings_in_session",
    "coerce_embedding_dimension",
    "generate_embedding",
    "generate_embeddings_batch",
    "upsert_embedding",
    "upsert_embedding_bg",
]


async def upsert_embedding(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    text: str,
    meta: dict[str, str],
) -> None:
    """Создаёт или обновляет эмбеддинг сущности в таблице portal_embedding."""
    if not get_settings().openai_api_key:
        logger.warning(
            "OPENAI_API_KEY не задан — индексация семантического поиска пропущена для %s#%s",
            entity_type,
            entity_id,
        )
        return

    try:
        embedding = await generate_embedding(text)
        vec_str = vec_literal(embedding)

        await db.execute(
            sa.text(UPSERT_EMBEDDING_SQL),
            {
                "id": str(uuid.uuid4()),
                "entity_type": entity_type,
                "entity_id": entity_id,
                "text_content": text,
                "vec": vec_str,
                "meta": json.dumps(meta, ensure_ascii=False),
            },
        )
        await db.commit()
        logger.debug("Эмбеддинг обновлён: %s#%s", entity_type, entity_id)
    except Exception:
        logger.exception("Ошибка обновления эмбеддинга %s#%s", entity_type, entity_id)


async def delete_embedding(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
) -> None:
    """Удаляет эмбеддинг сущности из portal_embedding."""
    await delete_embeddings_batch(db, entity_type, [entity_id])


async def delete_embeddings_in_session(
    db: AsyncSession,
    entity_type: str,
    entity_ids: list[str],
) -> None:
    """DELETE эмбеддингов без commit — вызывающий коммитит вместе с доменной операцией."""
    if not entity_ids:
        return
    await db.execute(
        sa_delete(PortalEmbedding).where(
            PortalEmbedding.entity_type == entity_type,
            PortalEmbedding.entity_id.in_(entity_ids),
        )
    )


async def delete_embeddings_batch(
    db: AsyncSession,
    entity_type: str,
    entity_ids: list[str],
) -> None:
    """Удаляет эмбеддинги нескольких сущностей одного типа (один commit)."""
    if not entity_ids:
        return
    try:
        await delete_embeddings_in_session(db, entity_type, entity_ids)
        await db.commit()
        logger.debug("Эмбеддинги удалены: %s × %d", entity_type, len(entity_ids))
    except Exception:
        logger.exception("Ошибка пакетного удаления эмбеддингов %s", entity_type)
