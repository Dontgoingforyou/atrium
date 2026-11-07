"""Эмбеддинги поиска при безвозвратном удалении документов."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_embedding import PortalEmbedding
from app.portal_documents.schemas.document import PortalDocumentCreate
from app.portal_documents.services.portal_document_mutations import create_document
from app.portal_documents.services.portal_document_trash import (
    DOCUMENT_TRASH_TTL_DAYS,
    permanently_purge_document,
    purge_expired_document_trash,
    soft_delete_document,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


async def _make_doc(session: AsyncSession, *, title: str = "Doc") -> Any:
    data = PortalDocumentCreate(title=title)
    return await create_document(session, data, author_sub="admin-sub")


@pytest.mark.asyncio
async def test_permanently_purge_deletes_embeddings(sqlite_session: AsyncSession) -> None:
    doc = await _make_doc(sqlite_session)
    sqlite_session.add(
        PortalEmbedding(
            entity_type="document",
            entity_id=str(doc.id),
            text_content="t",
            embedding=[0.0] * 8,
            meta={},
            updated_at=datetime.now(UTC),
        )
    )
    await sqlite_session.commit()

    with patch(
        "app.portal_documents.services.portal_document_trash.publish_document_mutation",
        new_callable=AsyncMock,
    ):
        await permanently_purge_document(sqlite_session, doc.id)

    remaining = (
        await sqlite_session.scalars(
            select(PortalEmbedding).where(
                PortalEmbedding.entity_type == "document",
                PortalEmbedding.entity_id == str(doc.id),
            )
        )
    ).all()
    assert remaining == []


@pytest.mark.asyncio
async def test_purge_expired_trash_deletes_embeddings_in_same_txn(
    sqlite_session: AsyncSession,
) -> None:
    doc = await _make_doc(sqlite_session, title="Просроченная корзина")
    sqlite_session.add(
        PortalEmbedding(
            entity_type="document",
            entity_id=str(doc.id),
            text_content="t",
            embedding=[0.0] * 8,
            meta={},
            updated_at=datetime.now(UTC),
        )
    )
    await sqlite_session.commit()

    with patch(
        "app.portal_documents.services.portal_document_trash.publish_document_mutation",
        new_callable=AsyncMock,
    ):
        await soft_delete_document(sqlite_session, doc.id, deleted_by_sub="admin-sub")
        expired_at = datetime.now(UTC) - timedelta(days=DOCUMENT_TRASH_TTL_DAYS + 1)
        await sqlite_session.execute(
            update(PortalDocument).where(PortalDocument.id == doc.id).values(deleted_at=expired_at)
        )
        await sqlite_session.commit()
        await purge_expired_document_trash(sqlite_session)

    remaining = (
        await sqlite_session.scalars(
            select(PortalEmbedding).where(
                PortalEmbedding.entity_type == "document",
                PortalEmbedding.entity_id == str(doc.id),
            )
        )
    ).all()
    assert remaining == []
    assert await sqlite_session.get(PortalDocument, doc.id) is None
