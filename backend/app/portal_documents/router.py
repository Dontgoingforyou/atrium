from fastapi import APIRouter

from app.portal_documents.routes.document_collab import internal_router as document_collab_internal_router
from app.portal_documents.routes.document_collab import router as document_collab_router
from app.portal_documents.routes.document_comments import router as document_comments_router
from app.portal_documents.routes.document_comments import ws_router as document_comments_ws_router
from app.portal_documents.routes.document_files import router as document_files_router
from app.portal_documents.routes.document_realtime import router as document_realtime_router
from app.portal_documents.routes.document_realtime import ws_router as document_realtime_ws_router
from app.portal_documents.routes.documents import admin_router, portal_router

portal_router.include_router(document_files_router)
portal_router.include_router(document_comments_router)
portal_router.include_router(document_realtime_router)
portal_router.include_router(document_collab_router)

# WS-маршруты без зависимостей авторизации по заголовку (тикет-авторизация).
ws_router = APIRouter()
ws_router.include_router(document_realtime_ws_router)
ws_router.include_router(document_comments_ws_router)

__all__ = ["portal_router", "admin_router", "ws_router", "document_collab_internal_router"]
