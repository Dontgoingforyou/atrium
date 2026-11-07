from __future__ import annotations

from fastapi import APIRouter

from app.api.deps_auth import NON_DEVELOPER_ROUTE_DEPENDENCIES
from app.portal_collab.routes import (
    agreements,
    notifications,
    rich_media,
    task_board_ws,
    task_columns,
    task_comments,
    task_files,
    task_links,
    task_page_ws,
    tasks,
)

router = APIRouter()
# HTTP-роуты — студентам запрещены
router.include_router(agreements.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
router.include_router(task_columns.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
router.include_router(tasks.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
router.include_router(task_comments.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
router.include_router(task_links.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
router.include_router(task_files.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
router.include_router(task_page_ws.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
# GET rich-media: object-level RBAC в сервисе (в т.ч. developer-docs для АУ).
router.include_router(rich_media.router)
router.include_router(notifications.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
# WS-роуты — аутентификация через тикеты; без студент-проверки (тикет заблокирован выше)
router.include_router(task_board_ws.router)
router.include_router(task_comments.ws_router)
router.include_router(task_page_ws.ws_router)
