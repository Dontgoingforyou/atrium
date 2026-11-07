from fastapi import APIRouter

from app.api.deps_auth import NON_DEVELOPER_ROUTE_DEPENDENCIES
from app.api.v1.routes import auth, auth_session, health, portal_account, portal_tags, portal_users
from app.api.v1.routes.portal_users import beacon_router as portal_users_beacon_router
from app.integrations.bench.routes import router as bench_export_router
from app.integrations.jira.routes import router as jira_integration_router
from app.portal_bench.router import router as portal_bench_router
from app.portal_calendar.router import invites_standalone as portal_calendar_invites_router
from app.portal_calendar.router import router as portal_calendar_router
from app.portal_calendar.router import ws_standalone as portal_calendar_ws_router
from app.portal_chat.router import router as portal_chat_router
from app.portal_collab.router import router as portal_collab_router
from app.portal_documents.router import admin_router as portal_docs_admin_router
from app.portal_documents.router import document_collab_internal_router as portal_docs_collab_internal_router
from app.portal_documents.router import portal_router as portal_docs_portal_router
from app.portal_documents.router import ws_router as portal_docs_ws_router
from app.portal_favorites.router import router as portal_favorites_router
from app.portal_finance.router import router as portal_finance_router
from app.portal_home.router import router as portal_home_router
from app.portal_learning.router import router as portal_learning_router
from app.portal_navigation.router import portal_router as portal_nav_portal_router
from app.portal_search.router import router as portal_search_router
from app.portal_specialists.router import router as portal_specialists_router
from app.portal_specialists.router import ws_router as portal_specialists_ws_router
from app.portal_telegram.router import router as portal_telegram_router
from app.portal_time_entries.router import router as portal_time_entries_router

api_router = APIRouter()
api_router.include_router(health.router, tags=["Служебное"])
api_router.include_router(auth.router, prefix="/auth", tags=["Авторизация"])
api_router.include_router(auth_session.router, prefix="/auth", tags=["Авторизация"])
api_router.include_router(portal_nav_portal_router)
api_router.include_router(portal_favorites_router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
api_router.include_router(portal_calendar_router)
api_router.include_router(portal_calendar_invites_router)
api_router.include_router(portal_calendar_ws_router)
api_router.include_router(portal_home_router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
api_router.include_router(portal_time_entries_router)
api_router.include_router(portal_bench_router)
api_router.include_router(portal_chat_router)  # зависимость применена внутри router.py модуля
api_router.include_router(portal_collab_router)  # зависимость применена внутри router.py модуля
api_router.include_router(portal_finance_router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
api_router.include_router(portal_learning_router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
api_router.include_router(portal_search_router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
api_router.include_router(portal_tags.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
# Чтение документов/навигации: RBAC в сервисах (в т.ч. developer-docs для АУ).
api_router.include_router(portal_docs_portal_router)
api_router.include_router(portal_docs_admin_router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
# Internal collab (Hocuspocus): только X-Collab-Service-Token, без JWT пользователя.
api_router.include_router(portal_docs_collab_internal_router)
# Префикс /portal нужен явно: ws_router не наследует его от portal_router.
api_router.include_router(portal_docs_ws_router, prefix="/portal")
api_router.include_router(portal_users.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
# Настройки аккаунта: timesheet-only могут читать/менять только guided_tour_completed (см. portal_account).
api_router.include_router(portal_account.router)
# Beacon-эндпоинты без глобальной зависимости авторизации.
api_router.include_router(portal_users_beacon_router)
api_router.include_router(portal_specialists_router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
api_router.include_router(portal_specialists_ws_router)
api_router.include_router(jira_integration_router)
# RAG: service Bearer, без JWT пользователя и без NON_DEVELOPER.
api_router.include_router(bench_export_router)
api_router.include_router(portal_telegram_router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
