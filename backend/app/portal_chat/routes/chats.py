from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, File, Form, Query, Response, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatMember
from app.infrastructure.ws import tickets as ws_ticket_svc
from app.infrastructure.ws.keepalive import is_pong, ws_keepalive
from app.infrastructure.ws.managers import get_chat_manager
from app.portal_chat.schemas.chat import (
    PortalChatCreate,
    PortalChatMemberInvite,
    PortalChatPatch,
    PortalChatRead,
    PortalChatWsTicketRead,
    PortalDirectChatCreate,
)
from app.portal_chat.services import chat as svc
from app.portal_chat.services import chat_avatar as chat_avatar_svc
from app.portal_chat.services import delete_chat as delete_chat_svc
from app.portal_chat.services import ephemeral_events as ephemeral_svc
from app.portal_chat.services import group_chat as group_svc
from app.schemas.auth import UserPublic
from app.services.avatar_presign import presign_avatar_url
from app.services.avatar_upload_common import AVATAR_MAX_BYTES
from app.services.portal_user import avatar_urls_for_subs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["Чаты"])
# WS-эндпоинты вынесены в отдельный роутер — они аутентифицируются через тикеты,
# а не через Authorization-заголовок, поэтому require_non_developer к ним неприменим.
ws_router = APIRouter(prefix="/portal", tags=["Чаты"])


def _dm_peer_sub(member_subs: list[str], current_sub: str) -> str | None:
    return next((s for s in member_subs if s != current_sub), None)


async def _enrich_chats(db: DbSession, chats: list[PortalChat], user: UserPublic) -> list[PortalChatRead]:
    """Обогащает список чатов участниками и счётчиком непрочитанных."""
    chat_ids = [c.id for c in chats]

    members_map: dict[uuid.UUID, list[str]] = {cid: [] for cid in chat_ids}
    if chat_ids:
        member_rows = (
            (await db.execute(select(PortalChatMember).where(PortalChatMember.chat_id.in_(chat_ids)))).scalars().all()
        )
        for m in member_rows:
            members_map[m.chat_id].append(m.user_sub)

    unread_map = await svc.get_batch_unread_counts(db, user.sub, chat_ids)

    dm_peer_subs: list[str] = []
    for chat in chats:
        if chat.canonical_dm_key is None or chat.avatar_storage_key:
            continue
        peer = _dm_peer_sub(members_map.get(chat.id, []), user.sub)
        if peer:
            dm_peer_subs.append(peer)
    dm_avatar_by_sub = await avatar_urls_for_subs(db, dm_peer_subs)

    result: list[PortalChatRead] = []
    for chat in chats:
        av_url = presign_avatar_url(chat.avatar_storage_key)
        if av_url is None and chat.canonical_dm_key is not None:
            peer = _dm_peer_sub(members_map.get(chat.id, []), user.sub)
            if peer:
                av_url = dm_avatar_by_sub.get(peer)
        read = PortalChatRead(
            id=chat.id,
            title=chat.title,
            created_by_sub=chat.created_by_sub,
            created_at=chat.created_at,
            updated_at=chat.updated_at,
            is_direct=chat.canonical_dm_key is not None,
            member_subs=members_map.get(chat.id, []),
            unread_count=unread_map.get(chat.id, 0),
            avatar_url=av_url,
            avatar_focal_x=chat.avatar_focal_x,
            avatar_focal_y=chat.avatar_focal_y,
            version=getattr(chat, "version", 1) or 1,
        )
        result.append(read)
    return result


@router.get(
    "/chats",
    summary="Список чатов текущего пользователя",
    response_model=list[PortalChatRead],
)
async def list_chats(
    user: CurrentUser,
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PortalChatRead]:
    chats = await svc.list_chats_for_user(
        db,
        user,
        skip=skip,
        limit=limit,
    )
    return await _enrich_chats(db, chats, user)


@router.post(
    "/chats",
    summary="Создать чат",
    response_model=PortalChatRead,
    status_code=201,
)
async def create_chat(
    user: CurrentUser,
    db: DbSession,
    body: PortalChatCreate,
) -> PortalChatRead:
    chat = await svc.create_chat(db, user, body)
    enriched = await _enrich_chats(db, [chat], user)
    return enriched[0]


@router.post(
    "/chats/direct",
    summary="Получить или создать прямой чат (DM) с другим пользователем",
    response_model=PortalChatRead,
)
async def get_or_create_direct_chat(
    user: CurrentUser,
    db: DbSession,
    body: PortalDirectChatCreate,
) -> PortalChatRead:
    chat = await svc.get_or_create_direct_chat(db, user, body.other_user_sub)
    enriched = await _enrich_chats(db, [chat], user)
    return enriched[0]


@router.patch(
    "/chats/{chat_id}",
    summary="Изменить название группового чата",
    response_model=PortalChatRead,
)
async def patch_group_chat(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalChatPatch,
) -> PortalChatRead:
    chat = await group_svc.patch_group_chat_title(
        db, user, chat_id, title=body.title, expected_version=body.expected_version
    )
    enriched = await _enrich_chats(db, [chat], user)
    return enriched[0]


@router.post(
    "/chats/{chat_id}/avatar",
    summary="Загрузить аватар группового чата",
    description=(
        f"Только создатель обычной группы. До {AVATAR_MAX_BYTES // (1024 * 1024)} МБ: JPEG, PNG, WebP или GIF."
    ),
)
async def post_group_chat_avatar(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    avatar_focal_x: float | None = Form(default=None),
    avatar_focal_y: float | None = Form(default=None),
) -> dict[str, object]:
    return await chat_avatar_svc.save_group_chat_avatar(
        db,
        user,
        chat_id,
        file=file,
        avatar_focal_x=avatar_focal_x,
        avatar_focal_y=avatar_focal_y,
    )


@router.delete(
    "/chats/{chat_id}/avatar",
    summary="Удалить аватар группового чата",
    status_code=204,
    response_class=Response,
)
async def delete_group_chat_avatar(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Response:
    await chat_avatar_svc.clear_group_chat_avatar(db, user, chat_id)
    return Response(status_code=204)


@router.delete(
    "/chats/{chat_id}",
    summary="Удалить чат целиком",
    description="DM — любой участник; группа — только создатель. История и вложения удаляются.",
    status_code=204,
    response_class=Response,
)
async def delete_chat(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Response:
    await delete_chat_svc.delete_entire_chat(db, user, chat_id)
    return Response(status_code=204)


@router.post(
    "/chats/{chat_id}/members",
    summary="Пригласить участника в групповой чат",
    status_code=204,
    response_class=Response,
)
async def invite_group_chat_member(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalChatMemberInvite,
) -> Response:
    await group_svc.add_member_to_group_chat(db, user, chat_id, new_member_sub=body.user_sub)
    return Response(status_code=204)


@router.delete(
    "/chats/{chat_id}/members/{user_sub}",
    summary="Исключить участника или покинуть групповой чат",
    status_code=204,
    response_class=Response,
)
async def remove_group_chat_member(
    chat_id: uuid.UUID,
    user_sub: str,
    user: CurrentUser,
    db: DbSession,
) -> Response:
    await group_svc.remove_member_from_group_chat(db, user, chat_id, target_sub=user_sub)
    return Response(status_code=204)


@router.post(
    "/chats/{chat_id}/ws-ticket",
    summary="Получить одноразовый тикет для WebSocket",
    response_model=PortalChatWsTicketRead,
    status_code=201,
)
async def create_chat_ws_ticket(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalChatWsTicketRead:
    """Выдаёт UUID, по которому можно подключить WS без передачи JWT в query (TTL 30 с)."""
    await svc.ensure_chat_read_access(db, user, chat_id)
    tick = await ws_ticket_svc.issue_chat_ws_ticket(chat_id, user)
    return PortalChatWsTicketRead(ticket=tick)


@router.post(
    "/chats/{chat_id}/read",
    summary="Отметить чат прочитанным (сбросить счётчик непрочитанных)",
    status_code=204,
)
async def mark_chat_read(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    """Выставляет last_read_at = now() для текущего пользователя в чате."""
    await svc.mark_chat_read(db, user, chat_id)


@ws_router.websocket("/chats/{chat_id}/ws")
async def chat_websocket(
    chat_id: uuid.UUID,
    websocket: WebSocket,
    db: DbSession,
    ticket: str = Query(..., min_length=8, description="Одноразовый тикет из POST .../ws-ticket"),
) -> None:
    """WebSocket для получения новых сообщений чата в реальном времени.

    Подключение: ``?ticket=<uuid>`` — тикен выдаётся авторизованным ``POST /chats/{id}/ws-ticket``.
    """
    parsed = await ws_ticket_svc.consume_chat_ws_ticket(ticket)
    if parsed is None:
        logger.warning("WS: невалидный или просроченный тикет chat_id=%s", chat_id)
        await websocket.close(code=4001)
        return
    t_chat_id, user = parsed
    if t_chat_id != chat_id:
        logger.warning("WS: несовпадение chat_id в тикете: path=%s ticket=%s", chat_id, t_chat_id)
        await websocket.close(code=4001)
        return

    try:
        await svc.ensure_chat_read_access(db, user, chat_id)
    except (ForbiddenError, NotFoundError):
        logger.warning("WS: нет доступа к chat_id=%s для sub=%s", chat_id, user.sub)
        await websocket.close(code=4001)
        return

    manager = get_chat_manager()
    await manager.connect(chat_id, websocket, user_sub=user.sub)
    async with ws_keepalive(websocket) as keepalive:
        try:
            while True:
                raw = await websocket.receive_text()
                if is_pong(raw):
                    keepalive.notify_pong()
                    continue
                client_event = ephemeral_svc.parse_client_ephemeral_event(raw)
                if client_event is None:
                    continue
                try:
                    await svc.ensure_chat_write_access(db, user, chat_id)
                except (ForbiddenError, NotFoundError):
                    logger.warning("WS: нет права писать в chat_id=%s для sub=%s", chat_id, user.sub)
                    await websocket.close(code=4001)
                    return
                if ephemeral_svc.should_rate_limit(
                    str(chat_id),
                    user.sub,
                    client_event["event"],
                    active=client_event["active"],
                ):
                    continue
                payload = ephemeral_svc.build_ephemeral_broadcast(client_event, user)
                await manager.publish(chat_id, payload)
        except WebSocketDisconnect:
            manager.disconnect(chat_id, websocket)
        except Exception as exc:
            logger.exception("WS: неожиданная ошибка (chat_id=%s): %s", chat_id, exc)
            manager.disconnect(chat_id, websocket)
