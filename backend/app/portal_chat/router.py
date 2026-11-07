from __future__ import annotations

from fastapi import APIRouter

from app.api.deps_auth import NON_DEVELOPER_ROUTE_DEPENDENCIES
from app.portal_chat.routes import chats, inbox, messages, push

router = APIRouter()
# HTTP-роуты — студентам запрещены
router.include_router(chats.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
router.include_router(messages.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
router.include_router(inbox.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
router.include_router(push.router, dependencies=NON_DEVELOPER_ROUTE_DEPENDENCIES)
# WS-роуты — аутентификация через тикеты; студенты не могут получить тикет (HTTP заблокирован)
router.include_router(chats.ws_router)
router.include_router(inbox.ws_router)
