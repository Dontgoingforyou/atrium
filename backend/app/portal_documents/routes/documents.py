"""HTTP-маршруты документов: чтение (portal) и мутации (admin)."""

from app.portal_documents.routes.documents_admin import admin_router
from app.portal_documents.routes.documents_portal import portal_router

__all__ = ["admin_router", "portal_router"]
