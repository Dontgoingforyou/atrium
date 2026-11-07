from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.infrastructure.db.models.portal_document import PortalDocument
from app.portal_documents.services.portal_document_queries import ensure_user_can_read_document


async def require_document_access(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalDocument:
    """Документ с проверкой RBAC."""
    return await ensure_user_can_read_document(db, user, document_id)


AccessibleDocument = Annotated[PortalDocument, Depends(require_document_access)]
