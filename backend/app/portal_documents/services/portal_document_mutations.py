from __future__ import annotations

import logging
import uuid
from types import SimpleNamespace
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.optimistic_lock import compare_and_swap_row
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_document import PortalDocument, PortalDocumentHistory
from app.portal_documents.schemas.document import PortalDocumentCreate, PortalDocumentUpdate
from app.portal_documents.services.portal_document_diff import compute_document_update_diff
from app.portal_documents.services.portal_document_queries import assert_no_document_parent_cycle, get_document
from app.portal_documents.services.portal_document_realtime import publish_document_mutation
from app.portal_documents.services.portal_document_shortcuts import sync_document_shortcuts
from app.schemas.auth import UserPublic
from app.services.portal_tags import replace_document_tags

logger = logging.getLogger(__name__)

_DOC_CAS_CONFLICT = "Документ изменён другим пользователем"
_ROW_FIELDS = frozenset({"title", "icon_emoji", "parent_document_id", "body", "owner_sub"})


async def write_document_history(
    session: AsyncSession,
    document_id: uuid.UUID,
    changed_by_sub: str,
    diff: dict[str, Any],
    *,
    changed_by_display_name: str | None = None,
    changed_by_email: str | None = None,
) -> None:
    entry = PortalDocumentHistory(
        document_id=document_id,
        changed_by_sub=changed_by_sub,
        changed_by_display_name=changed_by_display_name,
        changed_by_email=changed_by_email,
        changed_at=_now_utc(),
        diff=diff,
    )
    session.add(entry)


async def create_document(
    session: AsyncSession,
    data: PortalDocumentCreate,
    author_sub: str,
    author_display_name: str | None = None,
    author_email: str | None = None,
    author: UserPublic | None = None,
) -> PortalDocument:
    eff_parent = data.parent_document_id
    if eff_parent is not None:
        await get_document(session, eff_parent)

    min_so = await session.scalar(
        select(func.min(PortalDocument.sort_order)).where(
            PortalDocument.parent_document_id == eff_parent,
            PortalDocument.deleted_at.is_(None),
        )
    )
    init_sort = (min_so if min_so is not None else 0) - 1

    doc = PortalDocument(
        title=data.title,
        icon_emoji=data.icon_emoji,
        parent_document_id=eff_parent,
        body=data.body,
        author_sub=author_sub,
        author_display_name=author_display_name,
        author_email=author_email or None,
        owner_sub=data.owner_sub,
        sort_order=init_sort,
        version=1,
        created_at=_now_utc(),
        updated_at=_now_utc(),
    )
    session.add(doc)
    await session.flush()  # получаем doc.id до коммита

    if data.tag_ids:
        await replace_document_tags(session, doc.id, data.tag_ids)

    if data.body:
        await sync_document_shortcuts(session, doc.id, data.body, author=author)

    await write_document_history(
        session,
        doc.id,
        author_sub,
        {"action": {"old": None, "new": "created"}},
        changed_by_display_name=author_display_name,
        changed_by_email=author_email,
    )

    await session.commit()
    await publish_document_mutation(
        document_id=doc.id,
        parent_document_id=doc.parent_document_id,
    )
    return await get_document(session, doc.id)


async def update_document(
    session: AsyncSession,
    document_id: uuid.UUID,
    data: PortalDocumentUpdate,
    changed_by_sub: str,
    *,
    changed_by_display_name: str | None = None,
    changed_by_email: str | None = None,
    changed_by: UserPublic | None = None,
) -> PortalDocument:
    doc = await get_document(session, document_id)
    old_parent = doc.parent_document_id
    prev = SimpleNamespace(
        title=doc.title,
        icon_emoji=doc.icon_emoji,
        parent_document_id=doc.parent_document_id,
        body=doc.body,
        owner_sub=doc.owner_sub,
    )
    patch = data.model_dump(exclude_unset=True)
    patch.pop("expected_version", None)

    has_row_changes = bool(_ROW_FIELDS.intersection(patch))
    has_tags = data.tag_ids is not None
    if not has_row_changes and not has_tags:
        return doc

    if "parent_document_id" in patch:
        new_p = patch["parent_document_id"]
        if new_p is not None:
            await assert_no_document_parent_cycle(session, document_id, new_p)
            await get_document(session, new_p)

    values: dict[str, Any] = {"updated_at": _now_utc()}
    if data.title is not None:
        values["title"] = data.title
    if "icon_emoji" in patch:
        values["icon_emoji"] = data.icon_emoji
    if "parent_document_id" in patch:
        values["parent_document_id"] = patch["parent_document_id"]
    if data.body is not None:
        values["body"] = data.body
    if data.owner_sub is not None:
        values["owner_sub"] = data.owner_sub

    new_version = await compare_and_swap_row(
        session,
        PortalDocument,
        entity_id=document_id,
        expected_version=data.expected_version,
        values=values,
        conflict_message=_DOC_CAS_CONFLICT,
    )
    await session.refresh(doc)
    doc.version = new_version

    if data.tag_ids is not None:
        await replace_document_tags(session, document_id, data.tag_ids)

    if data.body is not None:
        await sync_document_shortcuts(session, document_id, data.body, author=changed_by)

    diff = compute_document_update_diff(prev, doc, patch, data)

    if diff:
        await write_document_history(
            session,
            document_id,
            changed_by_sub,
            diff,
            changed_by_display_name=changed_by_display_name,
            changed_by_email=changed_by_email,
        )

    extra_pages: set[uuid.UUID] = set()
    if old_parent != doc.parent_document_id:
        if old_parent is not None:
            extra_pages.add(old_parent)
        if doc.parent_document_id is not None:
            extra_pages.add(doc.parent_document_id)

    await session.commit()
    session.expire(doc, ["tags"])
    await publish_document_mutation(
        document_id=document_id,
        parent_document_id=doc.parent_document_id,
        extra_document_page_ids=extra_pages,
    )
    return await get_document(session, document_id)
