"""Векторный индекс документов, задач и сообщений чата."""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.portal_search_constants import (
    PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE,
    PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
    PORTAL_SEARCH_ENTITY_TYPE_TASK,
)
from app.infrastructure.db.session import async_session_factory
from app.portal_search.services.embedding import bulk_reindex

logger = logging.getLogger(__name__)

_TARGETS = (
    PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
    PORTAL_SEARCH_ENTITY_TYPE_TASK,
    PORTAL_SEARCH_ENTITY_TYPE_CHAT_MESSAGE,
)


async def vectorize_portal() -> dict[str, int]:
    """Посчитать векторы документов, задач и сообщений. Повтор перезаписывает те же строки."""
    async with async_session_factory() as session:
        totals = await bulk_reindex(session, list(_TARGETS))
    logger.info("Векторизация портала: %s", totals)
    return totals


async def vectorize_portal_if_local() -> dict[str, int] | None:
    """На старте с пустым ключом модели индекс строится сам. С ключом — только ``make seed``."""
    if get_settings().openai_api_key:
        return None
    return await vectorize_portal()
