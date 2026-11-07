"""HTTP: collab ticket для SPA и internal API для Hocuspocus."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Header, status

from app.api.deps import DbSession
from app.api.deps_auth import PortalManagerOrAdminUser
from app.core.config import get_settings
from app.portal_chat.schemas.chat import PortalChatWsTicketRead
from app.portal_documents.schemas.document_collab import (
    DocumentCollabAuthenticateRead,
    DocumentCollabAuthenticateRequest,
    DocumentCollabDocumentRead,
    DocumentCollabSnapshotRead,
    DocumentCollabSnapshotRequest,
)
from app.portal_documents.services import document_collab as collab_svc

# Тикет для SPA (manager/admin) — под /portal
router = APIRouter(tags=["Документы"])

# Internal для Hocuspocus — без JWT пользователя
internal_router = APIRouter(prefix="/internal/document-collab", tags=["Document collab (internal)"])


@router.post(
    "/documents/{document_id}/collab-ws-ticket",
    summary="Тикет Hocuspocus для совместного редактирования body",
    response_model=PortalChatWsTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_collab_ws_ticket(
    document_id: uuid.UUID,
    user: PortalManagerOrAdminUser,
    db: DbSession,
) -> PortalChatWsTicketRead:
    settings = get_settings()
    ticket = await collab_svc.issue_collab_ticket_for_manager(db, user, document_id, settings)
    return PortalChatWsTicketRead(ticket=ticket)


@internal_router.post(
    "/authenticate",
    summary="Hocuspocus onAuthenticate: снять тикет и вернуть контекст",
    response_model=DocumentCollabAuthenticateRead,
)
async def authenticate_document_collab(
    body: DocumentCollabAuthenticateRequest,
    db: DbSession,
    x_collab_service_token: str | None = Header(default=None, alias="X-Collab-Service-Token"),
) -> DocumentCollabAuthenticateRead:
    settings = get_settings()
    collab_svc.require_document_collab_service(settings, x_collab_service_token)
    return await collab_svc.authenticate_collab_ticket(db, body.ticket)


@internal_router.get(
    "/documents/{document_id}",
    summary="Загрузить body/version для hydrate Y.Doc",
    response_model=DocumentCollabDocumentRead,
)
async def load_document_collab(
    document_id: uuid.UUID,
    db: DbSession,
    x_collab_service_token: str | None = Header(default=None, alias="X-Collab-Service-Token"),
) -> DocumentCollabDocumentRead:
    settings = get_settings()
    collab_svc.require_document_collab_service(settings, x_collab_service_token)
    return await collab_svc.load_collab_document(db, document_id)


@internal_router.post(
    "/documents/{document_id}/snapshot",
    summary="CAS snapshot HTML body из Hocuspocus onStoreDocument",
    response_model=DocumentCollabSnapshotRead,
)
async def snapshot_document_collab(
    document_id: uuid.UUID,
    body: DocumentCollabSnapshotRequest,
    db: DbSession,
    x_collab_service_token: str | None = Header(default=None, alias="X-Collab-Service-Token"),
) -> DocumentCollabSnapshotRead:
    settings = get_settings()
    collab_svc.require_document_collab_service(settings, x_collab_service_token)
    return await collab_svc.snapshot_collab_body(
        db,
        document_id,
        body=body.body,
        expected_version=body.expected_version,
        actor_sub=body.actor_sub,
        actor_display_name=body.actor_display_name,
    )
