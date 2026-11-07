"""Фикстуры и хелперы для раздела «Документы для разработчиков»."""

from __future__ import annotations

from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.constants import DEVELOPER_DOCS_ROOT_ID, DEVELOPER_DOCS_TITLE
from sqlalchemy.ext.asyncio import AsyncSession


async def ensure_developer_docs_root(session: AsyncSession) -> PortalDocument:
    """Создать сид-корень developer-docs для SQLite create_all."""
    existing = await session.get(PortalDocument, DEVELOPER_DOCS_ROOT_ID)
    if existing is not None:
        return existing
    doc = PortalDocument(
        id=DEVELOPER_DOCS_ROOT_ID,
        title=DEVELOPER_DOCS_TITLE,
        author_sub="system",
        author_display_name="Система",
        body=None,
        sort_order=0,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    return doc
