"""Чанковая выборка и upsert эмбеддингов для bulk-reindex."""

from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.portal_search.services._embedding_generate import generate_embeddings_batch
from app.portal_search.services._embedding_sql import UPSERT_EMBEDDING_SQL, vec_literal


def upsert_params(
    entity_type: str,
    entity_id: str,
    text_content: str,
    vec_str: str,
    meta: dict[str, str],
) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "text_content": text_content,
        "vec": vec_str,
        "meta": json.dumps(meta, ensure_ascii=False),
    }


async def iter_select_chunks(db: AsyncSession, select_sql: str) -> AsyncIterator[list[Any]]:
    """Читать строки SELECT чанками (LIMIT/OFFSET), не загружая всю таблицу."""
    offset = 0
    chunk = get_settings().embedding_batch_size
    while True:
        result = await db.execute(
            sa.text(f"{select_sql} ORDER BY 1 LIMIT :chunk OFFSET :offset"),
            {"chunk": chunk, "offset": offset},
        )
        rows = list(result.fetchall())
        if not rows:
            return
        yield rows
        offset += len(rows)
        if len(rows) < chunk:
            return


async def upsert_embedding_rows(
    db: AsyncSession,
    entity_type: str,
    entity_ids: list[str],
    texts: list[str],
    metas: list[dict[str, str]],
) -> int:
    """Сгенерировать эмбеддинги и UPSERT один чанк. ``zip(..., strict=True)``."""
    if not texts:
        return 0
    embeddings = await generate_embeddings_batch(texts)
    params_list = [
        upsert_params(entity_type, eid, text, vec_literal(emb), meta)
        for eid, emb, text, meta in zip(entity_ids, embeddings, texts, metas, strict=True)
    ]
    await db.execute(sa.text(UPSERT_EMBEDDING_SQL), params_list)
    await db.commit()
    return len(params_list)
