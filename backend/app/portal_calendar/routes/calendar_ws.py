"""WebSocket сетки календаря: тикет и прокси к микросервису."""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Header, Query, WebSocket, WebSocketDisconnect, status
from websockets.asyncio.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed

from app.api.deps import HttpClient
from app.api.deps_auth import NonDeveloperUser
from app.core.config import get_settings
from app.portal_calendar.remote import require_remote
from app.portal_chat.schemas.chat import PortalChatWsTicketRead

router = APIRouter(prefix="/portal/calendar", tags=["Портал · Календарь"])
logger = logging.getLogger(__name__)


def _upstream_ws_base(http_base: str) -> str | None:
    base = http_base.strip().rstrip("/")
    if base.startswith("https://"):
        return "wss://" + base.removeprefix("https://")
    if base.startswith("http://"):
        return "ws://" + base.removeprefix("http://")
    return None


@router.post(
    "/ws-ticket",
    summary="Тикет WebSocket календаря (микросервис)",
    response_model=PortalChatWsTicketRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_calendar_ws_ticket(
    user: NonDeveloperUser,
    http: HttpClient,
    authorization: Annotated[str | None, Header()] = None,
) -> PortalChatWsTicketRead:
    ticket = await require_remote(user, authorization, http).issue_ws_ticket()
    return PortalChatWsTicketRead(ticket=ticket)


@router.websocket("/ws")
async def calendar_websocket(
    websocket: WebSocket,
    ticket: str = Query(..., min_length=8, description="Одноразовый тикет из POST /calendar/ws-ticket"),
) -> None:
    """Прокси сигнала «сетка изменилась» из микросервиса. Тела события в сокете нет."""
    upstream = _upstream_ws_base(get_settings().calendar_service_url)
    if upstream is None:
        await websocket.close(code=4001)
        return

    url = f"{upstream}/calendars/ws?ticket={quote(ticket, safe='')}"
    try:
        remote = await ws_connect(url)
    except Exception as exc:
        logger.warning("Calendar WS proxy: нет связи с микросервисом: %s", exc)
        await websocket.close(code=4001)
        return

    await websocket.accept()
    try:

        async def pump_client() -> None:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.disconnect":
                    return
                text = message.get("text")
                if text is not None:
                    await remote.send(text)

        async def pump_remote() -> None:
            async for message in remote:
                if isinstance(message, bytes):
                    await websocket.send_bytes(message)
                else:
                    await websocket.send_text(message)

        client_task = asyncio.create_task(pump_client())
        remote_task = asyncio.create_task(pump_remote())
        done, pending = await asyncio.wait(
            {client_task, remote_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            task_error = task.exception()
            if task_error is not None and not isinstance(task_error, (WebSocketDisconnect, ConnectionClosed)):
                raise task_error
    except WebSocketDisconnect:
        return
    except ConnectionClosed:
        return
    except Exception as exc:
        logger.exception("Calendar WS proxy: %s", exc)
        try:
            await websocket.close(code=4001)
        except Exception:
            return
    finally:
        await remote.close()
