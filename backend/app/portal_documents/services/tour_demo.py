"""Учебный документ guided tour в developer-docs (timesheet-only и полный контур)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.constants import DEVELOPER_DOCS_ROOT_ID
from app.portal_documents.services.portal_document_realtime import publish_document_mutation
from app.portal_documents.services.portal_document_trash import permanently_purge_document
from app.schemas.auth import UserPublic
from app.services import rbac as doc_rbac

logger = logging.getLogger(__name__)

TOUR_DEMO_DOCUMENT_TITLE = "Учебный документ"
TOUR_DEMO_DOCUMENT_BODY = (
    "<p>Это учебный документ для онбординга. Здесь обычно размещают регламенты и инструкции для разработчиков.</p>"
)


async def ensure_tour_demo_document(session: AsyncSession, user: UserPublic) -> tuple[PortalDocument, bool]:
    """Создать или вернуть учебный документ автора в developer-docs."""
    if not doc_rbac.user_can_access_developer_docs(user):
        logger.warning(
            "Отказ в доступе к tour-demo document: user_sub=%s",
            user.sub,
        )
        raise ForbiddenError("Раздел developer-docs недоступен для вашей роли")

    existing = await session.scalar(
        select(PortalDocument).where(
            PortalDocument.is_tour_demo.is_(True),
            PortalDocument.author_sub == user.sub,
            PortalDocument.deleted_at.is_(None),
        )
    )
    if existing is not None:
        return existing, False

    root = await session.get(PortalDocument, DEVELOPER_DOCS_ROOT_ID)
    if root is None:
        raise NotFoundError("Корень developer-docs не найден")

    timestamp = _now_utc()
    doc = PortalDocument(
        title=TOUR_DEMO_DOCUMENT_TITLE,
        parent_document_id=DEVELOPER_DOCS_ROOT_ID,
        body=TOUR_DEMO_DOCUMENT_BODY,
        author_sub=user.sub,
        author_display_name=user.full_name,
        author_email=user.email,
        is_tour_demo=True,
        sort_order=0,
        created_at=timestamp,
        updated_at=timestamp,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    await publish_document_mutation(
        document_id=doc.id,
        parent_document_id=doc.parent_document_id,
    )
    return doc, True


async def purge_tour_demo_documents(session: AsyncSession, user_sub: str) -> None:
    """Безвозвратно удалить учебные документы пользователя (завершение тура)."""
    doc_ids = list(
        (
            await session.scalars(
                select(PortalDocument.id).where(
                    PortalDocument.is_tour_demo.is_(True),
                    PortalDocument.author_sub == user_sub,
                )
            )
        ).all()
    )
    for doc_id in doc_ids:
        try:
            await permanently_purge_document(session, doc_id)
        except NotFoundError:
            continue
