from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationError
from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.services.portal_document_mutations import write_document_history
from app.portal_documents.services.portal_document_queries import _document_list_order, get_document
from app.portal_documents.services.portal_document_realtime import publish_document_mutation


async def reorder_document_among_siblings(
    session: AsyncSession,
    document_id: uuid.UUID,
    *,
    before_id: uuid.UUID | None,
    after_id: uuid.UUID | None,
    changed_by_sub: str,
    changed_by_display_name: str | None = None,
    changed_by_email: str | None = None,
) -> PortalDocument:
    """Переставить документ между соседями; ровно одно из ``before_id`` / ``after_id``."""
    if (before_id is None) == (after_id is None):
        raise ValidationError("Укажите ровно одно из полей: before_id или after_id")

    doc = await get_document(session, document_id)
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
    if document_id not in ids:
        raise ValidationError("Документ не найден среди активных соседей")

    rest = [i for i in ids if i != document_id]
    if before_id is not None:
        if before_id not in rest:
            raise ValidationError("before_id должен указывать на соседа")
        pos = rest.index(before_id)
    else:
        assert after_id is not None
        if after_id not in rest:
            raise ValidationError("after_id должен указывать на соседа")
        pos = rest.index(after_id) + 1

    new_order = rest[:pos] + [document_id] + rest[pos:]
    siblings_by_id = {s.id: s for s in siblings}
    for i, sid in enumerate(new_order, start=1):
        row = siblings_by_id.get(sid)
        if row is not None:
            row.sort_order = i

    await write_document_history(
        session,
        document_id,
        changed_by_sub,
        {"action": {"old": None, "new": "reordered"}},
        changed_by_display_name=changed_by_display_name,
        changed_by_email=changed_by_email,
    )
    await session.commit()
    await publish_document_mutation(
        document_id=document_id,
        parent_document_id=doc.parent_document_id,
    )
    return await get_document(session, document_id)
