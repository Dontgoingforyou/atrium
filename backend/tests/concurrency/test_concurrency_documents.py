"""Параллельные PATCH документа с одним expected_version (CAS)."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from app.core.exceptions import ConflictError
from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.schemas.document import PortalDocumentUpdate
from app.portal_documents.services import portal_document_mutations as doc_mut
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest.mark.asyncio
async def test_parallel_update_document_same_version_one_ok(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Два concurrent update с одним expected_version → один ok, один ConflictError."""

    async def _noop_publish(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(doc_mut, "publish_document_mutation", _noop_publish)

    doc_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(
            PortalDocument(
                id=doc_id,
                title="Doc",
                author_sub="author",
                body="v0",
                version=1,
            )
        )
        await s.commit()

    outcomes: list[str] = []

    async def try_update(body: str) -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await doc_mut.update_document(
                    sess,
                    doc_id,
                    PortalDocumentUpdate(expected_version=1, body=body),
                    changed_by_sub="writer",
                )
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    await asyncio.gather(try_update("from-a"), try_update("from-b"))

    assert sorted(outcomes) == ["conflict", "ok"]

    async with sqlite_concurrency_factory() as s:
        row = (await s.execute(select(PortalDocument).where(PortalDocument.id == doc_id))).scalar_one()
        assert row.version == 2
        assert row.body in ("from-a", "from-b")
