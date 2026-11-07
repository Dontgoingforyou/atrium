from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.api.deps_auth import NonDeveloperUser
from app.core.permissions import is_timesheet_only
from app.infrastructure.ws import tickets as ws_ticket_svc
from app.infrastructure.ws.keepalive import is_pong, ws_keepalive
from app.infrastructure.ws.managers import get_task_board_manager
from app.infrastructure.ws.room_manager import TASK_BOARD_ROOM_ID
from app.portal_chat.schemas.chat import PortalChatWsTicketRead

router = APIRouter(prefix="/portal", tags=["Задачи"])
logger = logging.getLogger(__name__)


@router.post(
    "/tasks/board/ws-ticket",
    summary="Тикет WebSocket доски задач (real-time)",
    response_model=PortalChatWsTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_task_board_ws_ticket(
    user: NonDeveloperUser,
) -> PortalChatWsTicketRead:
    t = await ws_ticket_svc.issue_task_board_ws_ticket(user)
    return PortalChatWsTicketRead(ticket=t)


@router.websocket("/tasks/board/ws")
async def task_board_websocket(
    websocket: WebSocket,
    ticket: str = Query(..., min_length=8, description="Одноразовый тикет из POST /tasks/board/ws-ticket"),
) -> None:
    """WebSocket: real-time события доски задач (task_created / task_updated / task_deleted).

    Доска — единая глобальная комната (``TASK_BOARD_ROOM_ID``), доступная всем пользователям
    портала с валидным тикетом, кроме режима «только таймшиты» (та же политика, что у HTTP
    роутов задач — ``NON_DEVELOPER_ROUTE_DEPENDENCIES``). Событие несёт только ``task_id`` /
    ``actor_sub`` / тип — клиент дотягивает содержимое через REST с полной проверкой RBAC.
    """
    user = await ws_ticket_svc.consume_task_board_ws_ticket(ticket)
    if user is None:
        await websocket.close(code=4001)
        return
    if is_timesheet_only(user):
        logger.warning("Task board WS: отказ в доступе (режим «только таймшиты») user_sub=%s", user.sub)
        await websocket.close(code=4001)
        return

    manager = get_task_board_manager()
    await manager.connect(TASK_BOARD_ROOM_ID, websocket)

    async with ws_keepalive(websocket) as keepalive:
        try:
            while True:
                raw = await websocket.receive_text()
                if is_pong(raw):
                    keepalive.notify_pong()
        except WebSocketDisconnect:
            manager.disconnect(TASK_BOARD_ROOM_ID, websocket)
        except Exception as exc:
            logger.exception("Task board WS: ошибка (user_sub=%s): %s", user.sub, exc)
            manager.disconnect(TASK_BOARD_ROOM_ID, websocket)
