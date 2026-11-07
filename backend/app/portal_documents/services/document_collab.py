"""Use cases для Hocuspocus: authenticate ticket, load/snapshot body (CAS)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import ForbiddenError, NotFoundError, ServiceUnavailableError, UnauthorizedError
from app.core.utils import hmac_secrets_equal
from app.infrastructure.ws import tickets as ws_ticket_svc
from app.portal_documents.schemas.document import PortalDocumentUpdate
from app.portal_documents.schemas.document_collab import (
    DocumentCollabAuthenticateRead,
    DocumentCollabDocumentRead,
    DocumentCollabSnapshotRead,
)
from app.portal_documents.services.portal_document_mutations import update_document
from app.portal_documents.services.portal_document_queries import (
    ensure_user_can_read_document,
    get_document,
)
from app.schemas.auth import UserPublic


def require_document_collab_service(settings: Settings, service_token: str | None) -> None:
    """Проверить, что collab включён и service token совпадает."""
    if not settings.document_collab_enabled:
        raise ServiceUnavailableError("Совместное редактирование документов отключено")
    expected = settings.document_collab_service_token.strip()
    if not expected:
        raise ServiceUnavailableError("Не настроен DOCUMENT_COLLAB_SERVICE_TOKEN")
    if not hmac_secrets_equal(service_token, expected):
        raise UnauthorizedError("Неверный service token collab")


def _display_name(user: UserPublic) -> str:
    return (user.full_name or user.email or user.username or user.sub).strip() or user.sub


async def authenticate_collab_ticket(
    session: AsyncSession,
    ticket: str,
) -> DocumentCollabAuthenticateRead:
    """Снять одноразовый тикет и вернуть контекст комнаты + body/version для hydrate."""
    parsed = await ws_ticket_svc.consume_document_collab_ws_ticket(ticket)
    if parsed is None:
        raise UnauthorizedError("Тикет collab недействителен или просрочен")
    document_id, user = parsed
    try:
        doc = await ensure_user_can_read_document(session, user, document_id)
    except (NotFoundError, ForbiddenError):
        raise UnauthorizedError("Нет доступа к документу для collab") from None
    return DocumentCollabAuthenticateRead(
        document_id=document_id,
        user_sub=user.sub,
        display_name=_display_name(user),
        version=doc.version,
        body=doc.body,
    )


async def load_collab_document(
    session: AsyncSession,
    document_id: uuid.UUID,
) -> DocumentCollabDocumentRead:
    doc = await get_document(session, document_id)
    return DocumentCollabDocumentRead(
        document_id=doc.id,
        version=doc.version,
        body=doc.body,
    )


async def snapshot_collab_body(
    session: AsyncSession,
    document_id: uuid.UUID,
    *,
    body: str | None,
    expected_version: int,
    actor_sub: str,
    actor_display_name: str | None,
) -> DocumentCollabSnapshotRead:
    """Записать HTML body через CAS (ConflictError пробрасывается наружу)."""
    data = PortalDocumentUpdate(expected_version=expected_version, body=body)
    doc = await update_document(
        session,
        document_id,
        data,
        changed_by_sub=actor_sub,
        changed_by_display_name=actor_display_name,
        changed_by_email=None,
        changed_by=None,
    )
    return DocumentCollabSnapshotRead(document_id=doc.id, version=doc.version)


async def issue_collab_ticket_for_manager(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
    settings: Settings,
) -> str:
    """Выдать тикет manager/admin после RBAC чтения документа."""
    if not settings.document_collab_enabled:
        raise ServiceUnavailableError("Совместное редактирование документов отключено")
    if not settings.document_collab_service_token.strip():
        raise ServiceUnavailableError("Не настроен DOCUMENT_COLLAB_SERVICE_TOKEN")
    await ensure_user_can_read_document(session, user, document_id)
    return await ws_ticket_svc.issue_document_collab_ws_ticket(document_id, user)
