"""WS карточки задачи: presence «сейчас на странице»."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.ws import tickets as ws_ticket_svc
from app.infrastructure.ws.keepalive import is_pong, ws_keepalive
from app.infrastructure.ws.managers import get_task_page_manager
from app.portal_chat.comment_thread_events import PAGE_VIEWERS_EVENT
from app.portal_chat.schemas.chat import PortalChatWsTicketRead
from app.portal_collab.services import task as svc
from app.schemas.auth import UserPublic

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Задачи"])
ws_router = APIRouter(tags=["Задачи"])


def _viewer_display_name(user: UserPublic) -> str:
    return (user.full_name or user.email or user.username or user.sub).strip() or user.sub


async def _publish_page_viewers(task_id: uuid.UUID) -> None:
    manager = get_task_page_manager()
    await manager.publish(
        task_id,
        {"event": PAGE_VIEWERS_EVENT, "viewers": manager.list_viewers(task_id)},
    )


@router.post(
    "/tasks/{task_id}/page-ws-ticket",
    summary="Тикет WebSocket presence карточки задачи",
    response_model=PortalChatWsTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_page_ws_ticket(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalChatWsTicketRead:
    await svc.get_task(db, user, task_id)
    t = await ws_ticket_svc.issue_task_page_ws_ticket(task_id, user)
    return PortalChatWsTicketRead(ticket=t)


@ws_router.websocket("/tasks/{task_id}/page-ws")
async def task_page_websocket(
    websocket: WebSocket,
    task_id: uuid.UUID,
    db: DbSession,
    ticket: str = Query(..., min_length=8),
) -> None:
    parsed = await ws_ticket_svc.consume_task_page_ws_ticket(ticket)
    if parsed is None:
        await websocket.close(code=4001)
        return
    tid, user = parsed
    if tid != task_id:
        await websocket.close(code=4001)
        return
    try:
        await svc.get_task(db, user, task_id)
    except (NotFoundError, ForbiddenError):
        await websocket.close(code=4001)
        return

    u = user if isinstance(user, UserPublic) else UserPublic.model_validate(user)
    manager = get_task_page_manager()
    await manager.connect(task_id, websocket, user_sub=u.sub, display_name=_viewer_display_name(u))
    await _publish_page_viewers(task_id)
    async with ws_keepalive(websocket) as keepalive:
        try:
            while True:
                raw = await websocket.receive_text()
                if is_pong(raw):
                    keepalive.notify_pong()
        except WebSocketDisconnect:
            manager.disconnect(task_id, websocket)
            await _publish_page_viewers(task_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Task page WS id=%s: %s", task_id, exc)
            manager.disconnect(task_id, websocket)
            await _publish_page_viewers(task_id)
