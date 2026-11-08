from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.api.deps_auth import CurrentUser
from app.infrastructure.db.session import (
    async_session_factory,
    skip_background_tasks_using_global_engine,
)
from app.infrastructure.ws import tickets as ws_ticket_svc
from app.infrastructure.ws.inbox_manager import get_inbox_manager
from app.infrastructure.ws.keepalive import is_pong, ws_keepalive
from app.portal_chat.schemas.chat import PortalInboxWsTicketRead
from app.services.portal_last_seen import finalize_last_seen_in_db
from app.services.portal_presence import record_presence, set_last_seen_iso_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["Чаты"])
ws_router = APIRouter(prefix="/portal", tags=["Чаты"])


@router.post(
    "/inbox/ws-ticket",
    summary="Одноразовый тикет для WebSocket инбокса (DM, уведомления)",
    response_model=PortalInboxWsTicketRead,
    status_code=201,
)
async def create_inbox_ws_ticket(user: CurrentUser) -> PortalInboxWsTicketRead:
    tick = await ws_ticket_svc.issue_inbox_ws_ticket(user)
    return PortalInboxWsTicketRead(ticket=tick)


@ws_router.websocket("/inbox/ws")
async def inbox_websocket(
    websocket: WebSocket,
    ticket: str = Query(..., min_length=8, description="Одноразовый тикет из POST .../ws-ticket"),
) -> None:
    """WebSocket: события ``dm_inbox_update``, ``portal_notification_update``
    и ``presence_update`` для текущего пользователя."""
    user = await ws_ticket_svc.consume_inbox_ws_ticket(ticket)
    if user is None:
        logger.warning("Inbox WS: невалидный или просроченный тикет")
        await websocket.close(code=4001)
        return

    manager = get_inbox_manager()
    await manager.connect(user.sub, websocket)

    # Помечаем пользователя онлайн и транслируем статус всем подключённым.
    await record_presence(user_sub=user.sub, visible=True, active=True)
    await manager.publish_presence(
        {
            "event": "presence_update",
            "sub": user.sub,
            "status": "online",
            "last_seen_at": datetime.now(UTC).isoformat(),
        },
    )

    async def _mark_offline_and_broadcast() -> None:
        """Фиксирует «был(а) только что» в Redis+БД и рассылает актуальный ``last_seen_at``.

        Без этого клиенты видят свежий ``status=offline``, но устаревший ``last_seen_at``
        из первичной загрузки (единый источник last seen:
        ``portal_presence.py`` + ``portal_last_seen.py``).
        """
        await record_presence(user_sub=user.sub, visible=False, active=False)
        offline_iso = datetime.now(UTC).isoformat()
        await set_last_seen_iso_now(user_sub=user.sub)
        # Глобальный engine — только вне pytest (тесты подменяют get_db_session на SQLite),
        # см. skip_background_tasks_using_global_engine и app/portal_chat/services/web_push.py.
        if not skip_background_tasks_using_global_engine():
            try:
                async with async_session_factory() as session:
                    await finalize_last_seen_in_db(session, user_sub=user.sub)
            except Exception:
                logger.exception(
                    "Inbox WS: не удалось обновить last_seen_at в БД (user_sub=%s)",
                    user.sub[:32],
                )
        await manager.publish_presence(
            {
                "event": "presence_update",
                "sub": user.sub,
                "status": "offline",
                "last_seen_at": offline_iso,
            },
        )

    async with ws_keepalive(websocket) as keepalive:
        try:
            while True:
                raw = await websocket.receive_text()
                if is_pong(raw):
                    keepalive.notify_pong()
        except WebSocketDisconnect:
            manager.disconnect(user.sub, websocket)
            # Помечаем офлайн только при закрытии последней вкладки (multi-tab safety).
            if not manager.has_connections(user.sub):
                await _mark_offline_and_broadcast()
        except Exception as exc:
            logger.exception("Inbox WS: неожиданная ошибка (user_sub=%s): %s", user.sub[:32], exc)
            manager.disconnect(user.sub, websocket)
            if not manager.has_connections(user.sub):
                await _mark_offline_and_broadcast()
