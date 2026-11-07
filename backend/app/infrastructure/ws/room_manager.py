"""Обобщённый менеджер WebSocket соединений «комната» + Redis pub/sub.

Канал: ``{prefix}:{room_id}`` (например ``chat:uuid``, ``task_comments:uuid``).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from collections import defaultdict
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket

logger = logging.getLogger(__name__)

_SUBSCRIBE_RETRY_SEC = 2

REDIS_CHANNEL_PREFIX_CHAT = "chat"
REDIS_CHANNEL_PREFIX_TASK_COMMENTS = "task_comments"
REDIS_CHANNEL_PREFIX_DOCUMENT_COMMENTS = "document_comments"
REDIS_CHANNEL_PREFIX_DOCUMENT_PAGE = "document_page"
REDIS_CHANNEL_PREFIX_TASK_PAGE = "task_page"
REDIS_CHANNEL_PREFIX_NAV_TREE = "nav_tree"
REDIS_CHANNEL_PREFIX_TASK_BOARD = "task_board"
REDIS_CHANNEL_PREFIX_SPECIALIST_BOARD = "specialist_board"
REDIS_CHANNEL_PREFIX_CALENDAR = "calendar"

# Фиксированный UUID «комнаты» для глобальной доски задач (все пользователи)
TASK_BOARD_ROOM_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
# Доска специалистов — одна комната для менеджеров и администраторов портала
SPECIALIST_BOARD_ROOM_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")
# Календарь портала — единая комната; клиент дотягивает данные через REST + RBAC
CALENDAR_ROOM_ID = uuid.UUID("00000000-0000-0000-0000-000000000004")


class TopicRoomManager:
    """WS-комнаты с одним префиксом Redis-канала."""

    def __init__(self, redis: aioredis.Redis | None, channel_prefix: str) -> None:
        self._redis = redis
        self._channel_prefix = channel_prefix
        self._local: dict[uuid.UUID, set[WebSocket]] = defaultdict(set)
        self._ws_user_sub: dict[WebSocket, str] = {}
        self._ws_viewer_meta: dict[WebSocket, dict[str, str]] = {}
        self._sub_tasks: dict[uuid.UUID, asyncio.Task[None]] = {}

    def _channel(self, room_id: uuid.UUID) -> str:
        return f"{self._channel_prefix}:{room_id}"

    async def connect(
        self,
        room_id: uuid.UUID,
        ws: WebSocket,
        *,
        user_sub: str | None = None,
        display_name: str | None = None,
    ) -> None:
        await ws.accept()
        self._local[room_id].add(ws)
        if user_sub is not None:
            self._ws_user_sub[ws] = user_sub
            self._ws_viewer_meta[ws] = {
                "sub": user_sub,
                "display_name": (display_name or user_sub).strip() or user_sub,
            }
        count = len(self._local[room_id])
        logger.info("WS подключён: %s, room_id=%s, клиентов=%d", self._channel_prefix, room_id, count)

        if self._redis and room_id not in self._sub_tasks:
            task = asyncio.create_task(self._subscribe(room_id), name=f"ws-sub-{self._channel_prefix}-{room_id}")
            self._sub_tasks[room_id] = task

    def disconnect(self, room_id: uuid.UUID, ws: WebSocket) -> None:
        self._local[room_id].discard(ws)
        self._ws_user_sub.pop(ws, None)
        self._ws_viewer_meta.pop(ws, None)
        remaining = len(self._local[room_id])
        logger.info("WS отключён: %s, room_id=%s, осталось=%d", self._channel_prefix, room_id, remaining)

        if remaining == 0:
            del self._local[room_id]
            task = self._sub_tasks.pop(room_id, None)
            if task and not task.done():
                task.cancel()

    def list_viewers(self, room_id: uuid.UUID) -> list[dict[str, str]]:
        """Уникальные viewers на инстансе (по sub) для presence-баннера."""
        by_sub: dict[str, dict[str, str]] = {}
        for ws in self._local.get(room_id, ()):
            meta = self._ws_viewer_meta.get(ws)
            if meta:
                by_sub[meta["sub"]] = meta
        return list(by_sub.values())

    async def disconnect_user(self, room_id: uuid.UUID, user_sub: str) -> None:
        """Закрывает локальные сокеты пользователя в комнате (после исключения из чата)."""
        sockets = [ws for ws in list(self._local.get(room_id, set())) if self._ws_user_sub.get(ws) == user_sub]
        for ws in sockets:
            self.disconnect(room_id, ws)
            with contextlib.suppress(Exception):
                await ws.close(code=4003)

    async def publish(self, room_id: uuid.UUID, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, default=str)
        channel = self._channel(room_id)
        if self._redis:
            try:
                await self._redis.publish(channel, data)
            except Exception as exc:
                logger.warning(
                    "Redis publish error %s room_id=%s: %s — локальная рассылка",
                    self._channel_prefix,
                    room_id,
                    exc,
                )
                await self._broadcast_local(room_id, data)
        else:
            await self._broadcast_local(room_id, data)

    async def _broadcast_local(self, room_id: uuid.UUID, data: str) -> None:
        sockets = list(self._local.get(room_id, set()))
        for ws in sockets:
            try:
                await ws.send_text(data)
            except Exception as exc:
                logger.warning("Ошибка отправки WS (%s, room_id=%s): %s", self._channel_prefix, room_id, exc)

    async def _subscribe(self, room_id: uuid.UUID) -> None:
        if self._redis is None:
            return
        channel = self._channel(room_id)
        try:
            while room_id in self._local:
                try:
                    async with self._redis.pubsub() as ps:
                        await ps.subscribe(channel)
                        logger.info("Redis подписка открыта: channel=%s", channel)
                        async for msg in ps.listen():
                            if msg["type"] == "message":
                                await self._broadcast_local(room_id, msg["data"])
                except asyncio.CancelledError:
                    logger.info("Redis подписка отменена: channel=%s", channel)
                    return
                except Exception as exc:
                    logger.exception(
                        "Ошибка Redis подписки %s room_id=%s: %s",
                        self._channel_prefix,
                        room_id,
                        exc,
                    )
                    if room_id not in self._local:
                        return
                    try:
                        await asyncio.sleep(_SUBSCRIBE_RETRY_SEC)
                    except asyncio.CancelledError:
                        return
        finally:
            self._sub_tasks.pop(room_id, None)
