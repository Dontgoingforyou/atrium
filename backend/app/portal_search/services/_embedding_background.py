"""Фоновые обёртки для upsert/delete/reindex эмбеддингов."""

from __future__ import annotations

from app.infrastructure.db.session import skip_background_tasks_using_global_engine


async def upsert_embedding_bg(
    entity_type: str,
    entity_id: str,
    text: str,
    meta: dict[str, str],
) -> None:
    """Вариант для FastAPI BackgroundTasks: открывает новую сессию БД."""
    if skip_background_tasks_using_global_engine():
        return
    from app.infrastructure.db.session import async_session_factory
    from app.portal_search.services.embedding import upsert_embedding

    async with async_session_factory() as session:
        await upsert_embedding(session, entity_type, entity_id, text, meta)


async def delete_embedding_bg(entity_type: str, entity_id: str) -> None:
    """Вариант для FastAPI BackgroundTasks: открывает новую сессию БД."""
    if skip_background_tasks_using_global_engine():
        return
    from app.infrastructure.db.session import async_session_factory
    from app.portal_search.services.embedding import delete_embedding

    async with async_session_factory() as session:
        await delete_embedding(session, entity_type, entity_id)


async def bulk_reindex_bg(targets: list[str], lock_token: str) -> None:
    """Вариант для FastAPI BackgroundTasks: открывает новую сессию БД."""
    from app.infrastructure.cache.reindex_lock import release_reindex_lock  # noqa: PLC0415

    try:
        if skip_background_tasks_using_global_engine():
            return
        from app.infrastructure.db.session import async_session_factory  # noqa: PLC0415
        from app.portal_search.services._embedding_bulk_reindex import bulk_reindex

        async with async_session_factory() as session:
            await bulk_reindex(session, targets)
    finally:
        await release_reindex_lock(lock_token)
