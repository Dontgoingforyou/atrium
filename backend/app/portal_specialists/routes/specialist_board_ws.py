from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.api.deps_auth import CurrentUser
from app.core.exceptions import ForbiddenError
from app.core.permissions import is_manager_or_admin
from app.infrastructure.ws import tickets as ws_ticket_svc
from app.infrastructure.ws.keepalive import is_pong, ws_keepalive
from app.infrastructure.ws.managers import get_specialist_board_manager
from app.infrastructure.ws.room_manager import SPECIALIST_BOARD_ROOM_ID
from app.portal_chat.schemas.chat import PortalChatWsTicketRead
from app.schemas.auth import UserPublic

router = APIRouter(prefix="/portal/specialists", tags=["Специалисты — доска"])
logger = logging.getLogger(__name__)


def _can_access_specialist_board_ws(user: UserPublic) -> bool:
    return is_manager_or_admin(user)


@router.post(
    "/board/ws-ticket",
    summary="Тикет WebSocket доски специалистов",
    response_model=PortalChatWsTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_specialist_board_ws_ticket(user: CurrentUser) -> PortalChatWsTicketRead:
    if not _can_access_specialist_board_ws(user):
        raise ForbiddenError("WebSocket доски специалистов — только для менеджера или администратора")
    ticket = await ws_ticket_svc.issue_specialist_board_ws_ticket(user)
    return PortalChatWsTicketRead(ticket=ticket)


@router.websocket("/board/ws")
async def specialist_board_websocket(
    websocket: WebSocket,
    ticket: str = Query(..., min_length=8, description="Одноразовый тикет из POST /board/ws-ticket"),
) -> None:
    ws_user = await ws_ticket_svc.consume_specialist_board_ws_ticket(ticket)
    if ws_user is None:
        await websocket.close(code=4001)
        return
    if not _can_access_specialist_board_ws(ws_user):
        await websocket.close(code=4003)
        return

    manager = get_specialist_board_manager()
    await manager.connect(SPECIALIST_BOARD_ROOM_ID, websocket)
    async with ws_keepalive(websocket) as keepalive:
        try:
            while True:
                raw = await websocket.receive_text()
                if is_pong(raw):
                    keepalive.notify_pong()
        except WebSocketDisconnect:
            manager.disconnect(SPECIALIST_BOARD_ROOM_ID, websocket)
        except Exception as exc:
            logger.exception("Specialist board WS: ошибка (user_sub=%s): %s", ws_user.sub, exc)
            manager.disconnect(SPECIALIST_BOARD_ROOM_ID, websocket)
