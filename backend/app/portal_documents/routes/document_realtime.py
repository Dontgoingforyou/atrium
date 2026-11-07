from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.api.deps_rbac import AccessibleDocument
from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.ws import tickets as ws_ticket_svc
from app.infrastructure.ws.keepalive import is_pong, ws_keepalive
from app.infrastructure.ws.managers import get_document_page_manager, get_nav_tree_manager
from app.portal_chat.comment_thread_events import PAGE_VIEWERS_EVENT
from app.portal_chat.schemas.chat import PortalChatWsTicketRead
from app.portal_documents.services.portal_document_queries import ensure_user_can_read_document
from app.schemas.auth import UserPublic
from app.services import rbac

logger = logging.getLogger(__name__)


def _viewer_display_name(user: UserPublic) -> str:
    return (user.full_name or user.email or user.username or user.sub).strip() or user.sub


async def _publish_page_viewers(manager: object, room_id: uuid.UUID) -> None:
    viewers = manager.list_viewers(room_id)  # type: ignore[attr-defined]
    await manager.publish(room_id, {"event": PAGE_VIEWERS_EVENT, "viewers": viewers})  # type: ignore[attr-defined]


# HTTP-маршруты: выдача тикетов (RBAC чтения — в сервисах / AccessibleDocument).
router = APIRouter(tags=["Документы"])
# WS-маршруты: аутентификация через тикет; подключаются к api_router БЕЗ NON_DEVELOPER_ROUTE_DEPENDENCIES,
# так как WebSocket не передаёт заголовок Authorization.
ws_router = APIRouter(tags=["Документы"])


# --- Открытая карточка / подстраницы: realtime по document_id ---


@router.post(
    "/documents/{document_id}/content-ws-ticket",
    summary="Тикет WebSocket обновлений тела/подстраниц документа",
    response_model=PortalChatWsTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_page_ws_ticket(
    doc: AccessibleDocument,
    user: CurrentUser,
) -> PortalChatWsTicketRead:
    t = await ws_ticket_svc.issue_document_page_ws_ticket(doc.id, user)
    return PortalChatWsTicketRead(ticket=t)


@ws_router.websocket("/documents/{document_id}/content-ws")
async def document_page_websocket(
    websocket: WebSocket,
    document_id: uuid.UUID,
    db: DbSession,
    ticket: str = Query(..., min_length=8, description="Одноразовый тикет"),
) -> None:
    parsed = await ws_ticket_svc.consume_document_page_ws_ticket(ticket)
    if parsed is None:
        await websocket.close(code=4001)
        return
    did, user = parsed
    if did != document_id:
        await websocket.close(code=4001)
        return
    try:
        u = user if isinstance(user, UserPublic) else UserPublic.model_validate(user)
        await ensure_user_can_read_document(db, u, document_id)
    except (NotFoundError, ForbiddenError):
        await websocket.close(code=4001)
        return

    manager = get_document_page_manager()
    await manager.connect(
        document_id,
        websocket,
        user_sub=u.sub,
        display_name=_viewer_display_name(u),
    )
    await _publish_page_viewers(manager, document_id)
    async with ws_keepalive(websocket) as keepalive:
        try:
            while True:
                raw = await websocket.receive_text()
                if is_pong(raw):
                    keepalive.notify_pong()
        except WebSocketDisconnect:
            manager.disconnect(document_id, websocket)
            await _publish_page_viewers(manager, document_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Document page WS id=%s: %s", document_id, exc)
            manager.disconnect(document_id, websocket)
            await _publish_page_viewers(manager, document_id)


# --- Глобальное дерево навигации: realtime для всех пользователей ---

# Фиксированный room_id — все пользователи подписаны на один broadcast-канал.
_NAV_TREE_ROOM_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


@router.post(
    "/navigation-tree-ws-ticket",
    summary="Тикет WebSocket обновлений дерева навигации (для всех пользователей)",
    response_model=PortalChatWsTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_nav_tree_ws_ticket(
    user: CurrentUser,
) -> PortalChatWsTicketRead:
    if not rbac.user_can_access_developer_docs(user):
        raise ForbiddenError("Нет доступа к документам")
    t = await ws_ticket_svc.issue_nav_tree_ws_ticket(user)
    return PortalChatWsTicketRead(ticket=t)


@ws_router.websocket("/navigation-tree-ws")
async def navigation_tree_websocket(
    websocket: WebSocket,
    ticket: str = Query(..., min_length=8, description="Одноразовый тикет"),
) -> None:
    user = await ws_ticket_svc.consume_nav_tree_ws_ticket(ticket)
    if user is None:
        await websocket.close(code=4001)
        return

    u = user if isinstance(user, UserPublic) else UserPublic.model_validate(user)
    if not rbac.user_can_access_developer_docs(u):
        await websocket.close(code=4001)
        return

    manager = get_nav_tree_manager()
    await manager.connect(_NAV_TREE_ROOM_ID, websocket)
    async with ws_keepalive(websocket) as keepalive:
        try:
            while True:
                raw = await websocket.receive_text()
                if is_pong(raw):
                    keepalive.notify_pong()
        except WebSocketDisconnect:
            manager.disconnect(_NAV_TREE_ROOM_ID, websocket)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Nav tree WS user=%s: %s", u.sub, exc)
            manager.disconnect(_NAV_TREE_ROOM_ID, websocket)
