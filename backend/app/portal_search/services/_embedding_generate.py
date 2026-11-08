"""Генерация векторных эмбеддингов.

Без ключа модели вектор считается локально. С ключом — через API эмбеддингов.
"""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from app.core.config import get_settings
from app.core.portal_search_constants import EMBEDDING_TEXT_MAX_CHARS
from app.portal_search.services._embedding_local import local_embedding
from app.services.openai_client import build_openai_client

logger = logging.getLogger(__name__)

_MAX_CHARS = EMBEDDING_TEXT_MAX_CHARS


def coerce_embedding_dimension(embedding: list[float], dimension: int) -> list[float]:
    """Приводит вектор к ``dimension``: короче — нули, длиннее — обрезка.

    Колонка ``portal_embedding.embedding`` и pgvector ``<=>`` требуют одну длину.
    Локальный прокси (Infinity) для той же модели может отдать 1024 вместо 1536 —
    без приведения поиск падает DataError, а не «ничего не найдено».
    """
    n = len(embedding)
    if n == dimension:
        return embedding
    if n < dimension:
        logger.warning(
            "Эмбеддинг провайдера: %s измерений, ожидается %s — дополняем нулями",
            n,
            dimension,
        )
        return list(embedding) + [0.0] * (dimension - n)
    logger.warning(
        "Эмбеддинг провайдера: %s измерений, ожидается %s — обрезаем",
        n,
        dimension,
    )
    return list(embedding[:dimension])


def _get_client() -> AsyncOpenAI:
    """Singleton AsyncOpenAI клиент (ленивая инициализация)."""
    s = get_settings()
    if not s.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY не задан. Добавьте его в .env чтобы включить семантический поиск.")
    return build_openai_client(api_key=s.openai_api_key, base_url=s.openai_base_url)


_client: AsyncOpenAI | None = None


def _client_singleton() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = _get_client()
    return _client


async def generate_embedding(text: str) -> list[float]:
    """Генерирует вектор эмбеддинга для одного текста через OpenAI API."""
    s = get_settings()
    if not text or not text.strip():
        return [0.0] * s.embedding_dimension

    text = text[:_MAX_CHARS]
    if not s.openai_api_key:
        return local_embedding(text, s.embedding_dimension)
    client = _client_singleton()
    response = await client.embeddings.create(
        input=text,
        model=s.embedding_model_name,
    )
    return coerce_embedding_dimension(response.data[0].embedding, s.embedding_dimension)


async def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Генерирует эмбеддинги для списка текстов батчами."""
    if not texts:
        return []

    s = get_settings()
    batch_size = s.embedding_batch_size
    zeros = [0.0] * s.embedding_dimension
    nonempty_idx = [i for i, t in enumerate(texts) if t and t.strip()]
    result: list[list[float]] = [list(zeros) for _ in texts]
    if not nonempty_idx:
        return result

    nonempty_texts = [texts[i][:_MAX_CHARS] for i in nonempty_idx]
    if not s.openai_api_key:
        for src_i, text in zip(nonempty_idx, nonempty_texts, strict=True):
            result[src_i] = local_embedding(text, s.embedding_dimension)
        return result

    client = _client_singleton()
    embeddings: list[list[float]] = []
    for i in range(0, len(nonempty_texts), batch_size):
        batch = nonempty_texts[i : i + batch_size]
        logger.info(
            "Генерация эмбеддингов батч %d/%d (%d текстов)",
            i // batch_size + 1,
            -(-len(nonempty_texts) // batch_size),
            len(batch),
        )
        response = await client.embeddings.create(input=batch, model=s.embedding_model_name)
        batch_vecs = [item.embedding for item in response.data]
        if len(batch_vecs) != len(batch):
            msg = f"OpenAI вернул {len(batch_vecs)} эмбеддингов вместо {len(batch)}"
            raise RuntimeError(msg)
        embeddings.extend(batch_vecs)

    for src_i, emb in zip(nonempty_idx, embeddings, strict=True):
        result[src_i] = coerce_embedding_dimension(emb, s.embedding_dimension)
    return result
