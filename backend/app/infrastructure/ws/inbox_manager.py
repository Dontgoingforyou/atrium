"""WebSocket-инбокс пользователя: Redis pub/sub на канал ``inbox:{user_sub}``.

События — обновления DM, портальных уведомлений и presence (``presence_update``);
клиент по ``event`` решает, какой REST-кэш инвалидировать.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket

logger = logging.getLogger(__name__)

_SUBSCRIBE_RETRY_SEC = 2

_manager: InboxManager | None = None

# Глобальный Redis-канал для рассылки presence-событий всем подключённым клиентам.
# Scope соответствует GET /portal/users/presence — открыто всем участникам портала.
GLOBAL_PRESENCE_CHANNEL = "portal:presence"

# Пер-пользовательский канал инбокса (WS + Telegram listener).
INBOX_CHANNEL_PREFIX = "inbox:"


def inbox_channel(user_sub: str) -> str:
    return f"{INBOX_CHANNEL_PREFIX}{user_sub}"


def inbox_channel_pattern() -> str:
    return f"{INBOX_CHANNEL_PREFIX}*"


def init_inbox_manager(redis: aioredis.Redis | None) -> None:
    global _manager
    _manager = InboxManager(redis=redis)
    logger.info("InboxManager инициализирован (Redis: %s)", "да" if redis else "нет — in-memory режим")


def get_inbox_manager() -> InboxManager:
    global _manager
    if _manager is None:
        _manager = InboxManager(redis=None)
    return _manager


class InboxManager:
    """WS по ``user_sub`` + Redis-канал ``inbox:{user_sub}``.

    Дополнительно: глобальный канал ``portal:presence`` для рассылки presence-событий
    (``presence_update``) всем подключённым пользователям без лишних REST-опросов.
    """

    def __init__(self, redis: aioredis.Redis | None) -> None:
        self._redis = redis
        self._local: dict[str, set[WebSocket]] = defaultdict(set)
        self._sub_tasks: dict[str, asyncio.Task[None]] = {}
        self._global_presence_task: asyncio.Task[None] | None = None

    async def connect(self, user_sub: str, ws: WebSocket) -> None:
        await ws.accept()
        self._local[user_sub].add(ws)
        count = len(self._local[user_sub])
        logger.info("Inbox WS подключён: user_sub (prefix)=%s…, клиентов=%d", user_sub[:24], count)

        if self._redis:
            if user_sub not in self._sub_tasks:
                short = f"{user_sub[:16]}…" if len(user_sub) > 16 else user_sub
                task = asyncio.create_task(self._subscribe(user_sub), name=f"inbox-sub-{short}")
                self._sub_tasks[user_sub] = task

            if self._global_presence_task is None or self._global_presence_task.done():
                self._global_presence_task = asyncio.create_task(
                    self._subscribe_global_presence(),
                    name="inbox-global-presence",
                )

    def disconnect(self, user_sub: str, ws: WebSocket) -> None:
        self._local[user_sub].discard(ws)
        remaining = len(self._local[user_sub])
        logger.info("Inbox WS отключён, осталось=%d", remaining)

        if remaining == 0:
            del self._local[user_sub]
            t = self._sub_tasks.pop(user_sub, None)
            if t and not t.done():
                t.cancel()

        if not self._local and self._global_presence_task and not self._global_presence_task.done():
            self._global_presence_task.cancel()
            self._global_presence_task = None

    def has_connections(self, user_sub: str) -> bool:
        """Возвращает True, если у пользователя есть хотя бы одно активное WS-соединение."""
        return bool(self._local.get(user_sub))

    async def publish(self, user_sub: str, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, default=str)
        if self._redis:
            try:
                await self._redis.publish(inbox_channel(user_sub), data)
            except Exception as exc:
                logger.warning("Redis publish error inbox: %s — локальная рассылка", exc)
                await self._broadcast_local(user_sub, data)
        else:
            await self._broadcast_local(user_sub, data)

    async def publish_presence(self, payload: dict[str, Any]) -> None:
        """Рассылает presence-событие всем подключённым пользователям через глобальный канал."""
        data = json.dumps(payload, default=str)
        if self._redis:
            try:
                await self._redis.publish(GLOBAL_PRESENCE_CHANNEL, data)
            except Exception as exc:
                logger.warning("Redis publish_presence error: %s — локальная рассылка", exc)
                await self._broadcast_all_local(data)
        else:
            await self._broadcast_all_local(data)

    async def _broadcast_local(self, user_sub: str, data: str) -> None:
        for ws in list(self._local.get(user_sub, set())):
            try:
                await ws.send_text(data)
            except Exception as exc:
                logger.warning("Inbox: ошибка send_text: %s", exc)

    async def _broadcast_all_local(self, data: str) -> None:
        """Рассылает сообщение всем локально подключённым пользователям."""
        for user_sub in list(self._local.keys()):
            await self._broadcast_local(user_sub, data)

    async def _subscribe(self, user_sub: str) -> None:
        if self._redis is None:
            return
        channel = inbox_channel(user_sub)
        try:
            while user_sub in self._local:
                try:
                    async with self._redis.pubsub() as ps:
                        await ps.subscribe(channel)
                        logger.info("Inbox: Redis подписка: channel=%s", channel)
                        async for msg in ps.listen():
                            if msg["type"] == "message":
                                await self._broadcast_local(user_sub, msg["data"])
                except asyncio.CancelledError:
                    logger.info("Inbox: подписка отменена: %s", channel)
                    return
                except Exception as exc:
                    logger.exception("Inbox: ошибка Redis для user_sub=%s: %s", user_sub, exc)
                    if user_sub not in self._local:
                        return
                    try:
                        await asyncio.sleep(_SUBSCRIBE_RETRY_SEC)
                    except asyncio.CancelledError:
                        return
        finally:
            self._sub_tasks.pop(user_sub, None)

    async def _subscribe_global_presence(self) -> None:
        """Подписывается на глобальный канал presence и рассылает события всем клиентам."""
        if self._redis is None:
            return
        try:
            while self._local:
                try:
                    async with self._redis.pubsub() as ps:
                        await ps.subscribe(GLOBAL_PRESENCE_CHANNEL)
                        logger.info("Inbox: Redis подписка на глобальный presence-канал")
                        async for msg in ps.listen():
                            if msg["type"] == "message":
                                await self._broadcast_all_local(msg["data"])
                except asyncio.CancelledError:
                    logger.info("Inbox: глобальная presence-подписка отменена")
                    return
                except Exception as exc:
                    logger.exception("Inbox: ошибка глобального presence-канала: %s", exc)
                    if not self._local:
                        return
                    try:
                        await asyncio.sleep(_SUBSCRIBE_RETRY_SEC)
                    except asyncio.CancelledError:
                        return
        finally:
            self._global_presence_task = None
