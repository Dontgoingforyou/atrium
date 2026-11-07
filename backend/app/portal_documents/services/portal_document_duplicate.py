from __future__ import annotations

import uuid
from collections import deque
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.services.portal_document_mutations import write_document_history
from app.portal_documents.services.portal_document_queries import (
    _document_list_order,
    document_subtree_ids,
    get_document,
)
from app.portal_documents.services.portal_document_realtime import publish_document_mutation
from app.portal_documents.services.portal_document_shortcuts import sync_document_shortcuts
from app.schemas.auth import UserPublic
from app.services.portal_tags import replace_document_tags


def _copy_title(source_title: str) -> str:
    suffix = " (копия)"
    base = source_title
    if base.endswith(suffix):
        base = base[: -len(suffix)]
    candidate = f"{base}{suffix}"
    return candidate[:512]


def _subtree_documents_bfs(
    root_id: uuid.UUID,
    docs_by_id: dict[uuid.UUID, PortalDocument],
) -> list[PortalDocument]:
    """Корень и потомки в порядке BFS (дети — по sort_order)."""
    children_by_parent: dict[uuid.UUID | None, list[PortalDocument]] = {}
    for doc in docs_by_id.values():
        children_by_parent.setdefault(doc.parent_document_id, []).append(doc)
    for kids in children_by_parent.values():
        kids.sort(key=lambda d: (d.sort_order, d.created_at, str(d.id)))

    ordered: list[PortalDocument] = []
    queue: deque[uuid.UUID] = deque([root_id])
    while queue:
        current_id = queue.popleft()
        current_doc = docs_by_id.get(current_id)
        if current_doc is None:
            continue
        ordered.append(current_doc)
        for child in children_by_parent.get(current_id, []):
            queue.append(child.id)
    return ordered


async def _load_subtree_documents(
    session: AsyncSession,
    subtree_ids: list[uuid.UUID],
) -> dict[uuid.UUID, PortalDocument]:
    if not subtree_ids:
        return {}
    stmt = (
        select(PortalDocument)
        .where(PortalDocument.id.in_(subtree_ids), PortalDocument.deleted_at.is_(None))
        .options(selectinload(PortalDocument.tags))
    )
    result = await session.execute(stmt)
    return {d.id: d for d in result.scalars().unique().all()}


async def _place_document_after_sibling(
    session: AsyncSession,
    document_id: uuid.UUID,
    after_id: uuid.UUID,
) -> None:
    """Вставить document_id сразу после after_id среди соседей (без commit)."""
    doc = await session.get(PortalDocument, document_id)
    if doc is None:
        return
    parent_id = doc.parent_document_id
    stmt = (
        select(PortalDocument)
        .where(
            PortalDocument.parent_document_id == parent_id,
            PortalDocument.deleted_at.is_(None),
        )
        .order_by(*_document_list_order())
    )
    siblings = list((await session.execute(stmt)).scalars().all())
    ids = [s.id for s in siblings]
    if document_id not in ids or after_id not in ids:
        return
    rest = [i for i in ids if i != document_id]
    pos = rest.index(after_id) + 1
    new_order = rest[:pos] + [document_id] + rest[pos:]
    siblings_by_id = {s.id: s for s in siblings}
    for i, sid in enumerate(new_order, start=1):
        row = siblings_by_id.get(sid)
        if row is not None:
            row.sort_order = i


async def duplicate_document_subtree(
    session: AsyncSession,
    source_id: uuid.UUID,
    author_sub: str,
    *,
    author_display_name: str | None = None,
    author_email: str | None = None,
    author: UserPublic | None = None,
) -> PortalDocument:
    """Скопировать документ и всё поддерево; копия-корень — сосед сразу после оригинала."""
    source = await get_document(session, source_id)
    subtree_ids = await document_subtree_ids(session, source_id)
    docs_by_id = await _load_subtree_documents(session, subtree_ids)
    ordered = _subtree_documents_bfs(source_id, docs_by_id)
    id_map: dict[uuid.UUID, uuid.UUID] = {}
    root_copy_id: uuid.UUID | None = None
    now = _now_utc()

    for doc in ordered:
        is_root = doc.id == source_id
        if is_root:
            new_parent_id = source.parent_document_id
            new_title = _copy_title(source.title)
        else:
            parent_old = doc.parent_document_id
            assert parent_old is not None
            new_parent_id = id_map[parent_old]
            new_title = doc.title

        copy = PortalDocument(
            title=new_title,
            icon_emoji=doc.icon_emoji,
            parent_document_id=new_parent_id,
            body=doc.body,
            author_sub=author_sub,
            author_display_name=author_display_name,
            author_email=author_email or None,
            owner_sub=doc.owner_sub,
            sort_order=doc.sort_order,
            created_at=now,
            updated_at=now,
        )
        session.add(copy)
        await session.flush()
        id_map[doc.id] = copy.id
        if is_root:
            root_copy_id = copy.id

        tag_ids = [t.id for t in doc.tags]
        if tag_ids:
            await replace_document_tags(session, copy.id, tag_ids)

        if copy.body:
            await sync_document_shortcuts(session, copy.id, copy.body, author=author)

    assert root_copy_id is not None
    await _place_document_after_sibling(session, root_copy_id, source_id)

    diff: dict[str, Any] = {
        "action": {"old": None, "new": "duplicated"},
        "source_document_id": {"old": None, "new": str(source_id)},
    }
    await write_document_history(
        session,
        root_copy_id,
        author_sub,
        diff,
        changed_by_display_name=author_display_name,
        changed_by_email=author_email,
    )

    await session.commit()
    root_copy = await get_document(session, root_copy_id)
    await publish_document_mutation(
        document_id=root_copy.id,
        parent_document_id=root_copy.parent_document_id,
    )
    return root_copy
