from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql import Select

from app.core.exceptions import NotFoundError, ValidationError
from app.core.portal_search_constants import PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.services.portal_document_mutations import write_document_history
from app.portal_documents.services.portal_document_queries import document_subtree_ids, get_document
from app.portal_documents.services.portal_document_realtime import publish_document_mutation
from app.portal_favorites.services.favorite import remove_favorites_for_documents
from app.portal_search.services.embedding import delete_embeddings_in_session

DOCUMENT_TRASH_TTL_DAYS = 90


async def _purge_document_embeddings(session: AsyncSession, tree_ids: list[uuid.UUID]) -> None:
    """Удаляет эмбеддинги поиска для всех документов поддерева."""
    if not tree_ids:
        return
    await delete_embeddings_in_session(
        session,
        PORTAL_SEARCH_ENTITY_TYPE_DOCUMENT,
        [str(doc_id) for doc_id in tree_ids],
    )


async def _ensure_trash_tree_root(session: AsyncSession, doc: PortalDocument) -> None:
    """Операции корзины из UI выполняются над корнем удалённого дерева."""
    if doc.parent_document_id is None:
        return
    parent = await session.get(PortalDocument, doc.parent_document_id)
    if parent is not None and parent.deleted_at is not None:
        raise ValidationError("Выберите корневой документ в корзине")


async def soft_delete_document(
    session: AsyncSession,
    document_id: uuid.UUID,
    deleted_by_sub: str,
    *,
    deleted_by_display_name: str | None = None,
    deleted_by_email: str | None = None,
) -> list[uuid.UUID]:
    """Пометить документ и поддерево как удалённые.

    Избранное не снимается: список скрывает документ в корзине, restore вернёт звёзды.
    """
    doc_row = await session.get(PortalDocument, document_id)
    if doc_row is None:
        raise NotFoundError("Документ не найден")
    tree_ids = await document_subtree_ids(session, document_id, include_deleted=True)
    if doc_row.deleted_at is not None:
        return tree_ids

    doc = await get_document(session, document_id)
    now = _now_utc()
    child_ids = [tid for tid in tree_ids if tid != document_id]
    if child_ids:
        await session.execute(
            update(PortalDocument)
            .where(PortalDocument.id.in_(child_ids))
            .values(
                deleted_at=now,
                deleted_by_sub=None,
                deleted_by_display_name=None,
                deleted_by_email=None,
            )
        )
    await session.execute(
        update(PortalDocument)
        .where(PortalDocument.id == document_id)
        .values(
            deleted_at=now,
            deleted_by_sub=deleted_by_sub,
            deleted_by_display_name=deleted_by_display_name,
            deleted_by_email=deleted_by_email,
        )
    )

    await write_document_history(
        session,
        document_id,
        deleted_by_sub,
        {"action": {"old": None, "new": "deleted"}},
        changed_by_display_name=deleted_by_display_name,
        changed_by_email=deleted_by_email,
    )
    await session.commit()
    await publish_document_mutation(
        document_id=document_id,
        parent_document_id=doc.parent_document_id,
    )
    return tree_ids


async def restore_document(
    session: AsyncSession,
    document_id: uuid.UUID,
    changed_by_sub: str,
    *,
    changed_by_display_name: str | None = None,
    changed_by_email: str | None = None,
) -> PortalDocument:
    """Снять пометку корзины с дерева."""
    doc = await get_document(session, document_id, include_deleted=True)
    if doc.deleted_at is None:
        return await get_document(session, document_id)
    await _ensure_trash_tree_root(session, doc)

    tree_ids = await document_subtree_ids(session, document_id, include_deleted=True)
    await session.execute(
        update(PortalDocument)
        .where(PortalDocument.id.in_(tree_ids))
        .values(
            deleted_at=None,
            deleted_by_sub=None,
            deleted_by_display_name=None,
            deleted_by_email=None,
        )
    )

    await write_document_history(
        session,
        document_id,
        changed_by_sub,
        {"action": {"old": "deleted", "new": "restored"}},
        changed_by_display_name=changed_by_display_name,
        changed_by_email=changed_by_email,
    )
    await session.commit()
    await publish_document_mutation(
        document_id=document_id,
        parent_document_id=doc.parent_document_id,
    )
    return await get_document(session, document_id)


async def permanently_purge_document(session: AsyncSession, document_id: uuid.UUID) -> list[uuid.UUID]:
    """Безвозвратное удаление строки и поддерева из БД."""
    from app.portal_documents.services import document_file as document_file_svc

    doc = await get_document(session, document_id, include_deleted=True)
    if doc.deleted_at is not None:
        await _ensure_trash_tree_root(session, doc)
    parent_document_id = doc.parent_document_id
    tree_ids = await document_subtree_ids(session, document_id, include_deleted=True)
    await document_file_svc.purge_storage_for_document_tree(session, document_id)
    await remove_favorites_for_documents(session, tree_ids)
    await _purge_document_embeddings(session, tree_ids)
    await session.delete(doc)
    await session.commit()
    await publish_document_mutation(
        document_id=document_id,
        parent_document_id=parent_document_id,
    )
    return tree_ids


async def purge_expired_document_trash(session: AsyncSession) -> None:
    """Удаляет из БД корни корзины старше ``DOCUMENT_TRASH_TTL_DAYS`` (для фона и тестов)."""
    await _purge_expired_trash(session)


def _trash_roots_base_stmt(*, expired_before: datetime | None = None) -> Select[Any]:
    """Базовый запрос корней удалённых деревьев (не дочерних внутри удалённого родителя)."""
    parent_tab = aliased(PortalDocument)
    stmt = (
        select(PortalDocument)
        .where(PortalDocument.deleted_at.is_not(None))
        .outerjoin(parent_tab, PortalDocument.parent_document_id == parent_tab.id)
        .where(
            or_(
                PortalDocument.parent_document_id.is_(None),
                parent_tab.deleted_at.is_(None),
            )
        )
    )
    if expired_before is not None:
        stmt = stmt.where(PortalDocument.deleted_at < expired_before)
    return stmt


async def _batch_permanently_purge_roots(session: AsyncSession, root_ids: list[uuid.UUID]) -> None:
    """Безвозвратное удаление нескольких корней корзины одной транзакцией."""
    from app.portal_documents.services import document_file as document_file_svc

    if not root_ids:
        return

    roots = (
        await session.execute(
            select(
                PortalDocument.id,
                PortalDocument.parent_document_id,
            ).where(PortalDocument.id.in_(root_ids))
        )
    ).all()

    all_tree_ids: list[uuid.UUID] = []
    all_storage_keys: list[str] = []
    for rid in root_ids:
        tree_ids = await document_subtree_ids(session, rid, include_deleted=True)
        all_tree_ids.extend(tree_ids)
        all_storage_keys.extend(await document_file_svc.collect_storage_keys_for_documents(session, tree_ids))
    unique_tree_ids = list(dict.fromkeys(all_tree_ids))

    if all_storage_keys:
        from app.infrastructure.storage.client import async_delete_objects

        await async_delete_objects(list(dict.fromkeys(all_storage_keys)))

    await remove_favorites_for_documents(session, unique_tree_ids)
    await _purge_document_embeddings(session, unique_tree_ids)
    await session.execute(delete(PortalDocument).where(PortalDocument.id.in_(root_ids)))
    await session.commit()
    for row in roots:
        await publish_document_mutation(
            document_id=row.id,
            parent_document_id=row.parent_document_id,
        )


async def _purge_expired_trash(session: AsyncSession) -> None:
    cutoff = _now_utc() - timedelta(days=DOCUMENT_TRASH_TTL_DAYS)
    rows = (await session.execute(_trash_roots_base_stmt(expired_before=cutoff))).scalars().all()
    root_ids = [row.id for row in rows]
    await _batch_permanently_purge_roots(session, root_ids)


async def count_trash_document_roots(session: AsyncSession) -> int:
    """Число корней в корзине (без учёта дочерних страниц удалённого дерева)."""
    subq = _trash_roots_base_stmt().subquery()
    return int(await session.scalar(select(func.count()).select_from(subq)) or 0)


async def list_trash_document_roots(
    session: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[PortalDocument]:
    """Список верхних удалённых документов.

    Истёкший TTL обрабатывается фоновой задачей ``document_trash_nightly``, не на каждом GET.
    """
    stmt = _trash_roots_base_stmt().order_by(PortalDocument.deleted_at.desc()).offset(skip).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
