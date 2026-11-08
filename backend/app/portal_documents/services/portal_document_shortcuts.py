"""Парсинг documentLink из HTML body и синхронизация portal_document_shortcut."""

from __future__ import annotations

import logging
import re
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.portal_document import PortalDocument, PortalDocumentShortcut
from app.portal_documents.services.portal_document_queries import developer_docs_readable_ids
from app.schemas.auth import UserPublic
from app.services import rbac

logger = logging.getLogger(__name__)

# Атрибут ярлыка TipTap DocumentLink (единый контракт с фронтом).
_DOCUMENT_ID_ATTR_RE = re.compile(
    r'data-document-id\s*=\s*["\']([0-9a-fA-F-]{36})["\']',
    re.IGNORECASE,
)


def extract_document_link_ids_from_body(body: str | None) -> list[uuid.UUID]:
    """Уникальные UUID из data-document-id в порядке первого появления."""
    if not body:
        return []
    seen: set[uuid.UUID] = set()
    ordered: list[uuid.UUID] = []
    for match in _DOCUMENT_ID_ATTR_RE.finditer(body):
        raw = match.group(1)
        try:
            doc_id = uuid.UUID(raw)
        except ValueError:
            continue
        if doc_id in seen:
            continue
        seen.add(doc_id)
        ordered.append(doc_id)
    return ordered


async def _filter_targets_by_author_access(
    session: AsyncSession,
    author: UserPublic,
    target_ids: list[uuid.UUID],
) -> list[uuid.UUID]:
    """Отбросить target, к которым у автора source-документа нет доступа.

    Ярлык — вторичная операция над target-документом: сам факт «target существует и не удалён»
    недостаточен — иначе автор мог бы подставить угаданный/скопированный
    чужой UUID и сохранить на него ссылку, к которой сам не имеет доступа.
    """
    if rbac.user_can_access_documents(author):
        return target_ids
    if rbac.user_can_access_developer_docs(author):
        dev_ids = set(await developer_docs_readable_ids(session))
        allowed = [tid for tid in target_ids if tid in dev_ids]
        dropped = [tid for tid in target_ids if tid not in dev_ids]
        if dropped:
            logger.warning(
                "Ярлык(и) documentLink вне доступных автору разделов отброшены: author_sub=%s target_ids=%s",
                author.sub,
                dropped,
            )
        return allowed
    logger.warning(
        "Ярлыки documentLink отброшены — автор не имеет доступа к документам: author_sub=%s",
        author.sub,
    )
    return []


async def sync_document_shortcuts(
    session: AsyncSession,
    source_document_id: uuid.UUID,
    body: str | None,
    author: UserPublic | None = None,
) -> None:
    """Заменить ярлыки source по содержимому body (в той же транзакции, что update).

    - self-link пропускаются;
    - target, уже являющийся реальным child source, не дублируется ярлыком;
    - несуществующие / soft-deleted target не сохраняются;
    - target, недоступный автору по RBAC (см. `_filter_targets_by_author_access`),
      не сохраняется — передавайте `author`, если он известен на месте вызова.
    """
    desired = extract_document_link_ids_from_body(body)
    desired = [tid for tid in desired if tid != source_document_id]

    child_ids: set[uuid.UUID] = set()
    if desired:
        child_rows = (
            (
                await session.execute(
                    select(PortalDocument.id).where(
                        PortalDocument.parent_document_id == source_document_id,
                        PortalDocument.deleted_at.is_(None),
                        PortalDocument.id.in_(desired),
                    )
                )
            )
            .scalars()
            .all()
        )
        child_ids = set(child_rows)

    desired = [tid for tid in desired if tid not in child_ids]

    existing_targets: set[uuid.UUID] = set()
    if desired:
        existing_targets = set(
            (
                await session.execute(
                    select(PortalDocument.id).where(
                        PortalDocument.id.in_(desired),
                        PortalDocument.deleted_at.is_(None),
                    )
                )
            )
            .scalars()
            .all()
        )
    desired = [tid for tid in desired if tid in existing_targets]

    if author is not None and desired:
        desired = await _filter_targets_by_author_access(session, author, desired)

    await session.execute(
        delete(PortalDocumentShortcut).where(PortalDocumentShortcut.source_document_id == source_document_id)
    )
    for target_id in desired:
        session.add(
            PortalDocumentShortcut(
                source_document_id=source_document_id,
                target_document_id=target_id,
            )
        )
