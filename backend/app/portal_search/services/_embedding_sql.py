"""Общий SQL-шаблон и форматирование вектора для upsert эмбеддингов в pgvector.

Выделено в отдельный leaf-модуль без зависимостей от `embedding.py` / `_embedding_bulk_reindex.py` /
`_embedding_specialists.py` (устраняет тройное дублирование `_vec_literal` и двойное — `_UPSERT_SQL`,
которое накопилось в этих трёх файлах пакета, dry.mdc). Отдельный модуль, а не общая точка вроде
`embedding.py`, — чтобы не создать цикл импортов: `embedding.py` сам импортирует `_embedding_bulk_reindex.py`,
а тот — `_embedding_specialists.py`.
"""

from __future__ import annotations

UPSERT_EMBEDDING_SQL = """
INSERT INTO portal_embedding
    (id, entity_type, entity_id, text_content, embedding, meta, updated_at)
VALUES
    (:id, :entity_type, :entity_id, :text_content, CAST(:vec AS vector), :meta, now())
ON CONFLICT (entity_type, entity_id) DO UPDATE SET
    text_content = EXCLUDED.text_content,
    embedding    = EXCLUDED.embedding,
    meta         = EXCLUDED.meta,
    updated_at   = now()
"""


def vec_literal(embedding: list[float]) -> str:
    """Форматирует вектор как строку '[1.2,3.4,...]' для передачи в pgvector через cast."""
    return "[" + ",".join(f"{v:.8f}" for v in embedding) + "]"
