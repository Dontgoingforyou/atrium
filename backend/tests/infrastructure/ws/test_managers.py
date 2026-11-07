"""Публичные правила InboxManager / TopicRoomManager (не домен чата)."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.ws import inbox_manager as im_mod
from app.infrastructure.ws.room_manager import REDIS_CHANNEL_PREFIX_CHAT, TopicRoomManager


async def test_inbox_manager_subscribe_delivers_redis_message() -> None:
    delivered = asyncio.Event()

    @asynccontextmanager
    async def _pubsub_cm() -> AsyncIterator[MagicMock]:
        ps = MagicMock()
        ps.subscribe = AsyncMock()

        async def _listen() -> object:
            yield {"type": "message", "data": json.dumps({"event": "ping"})}
            await asyncio.sleep(3600)

        ps.listen = _listen
        yield ps

    redis = MagicMock()
    redis.pubsub = MagicMock(side_effect=lambda: _pubsub_cm())
    mgr = im_mod.InboxManager(redis=redis)
    ws = AsyncMock()
    ws.accept = AsyncMock()

    async def _send_text(_data: str) -> None:
        delivered.set()

    ws.send_text = AsyncMock(side_effect=_send_text)
    await mgr.connect("user-for-sub", ws)
    await asyncio.wait_for(delivered.wait(), timeout=1.0)
    ws.send_text.assert_awaited()
    assert json.loads(ws.send_text.await_args.args[0]) == {"event": "ping"}
    mgr.disconnect("user-for-sub", ws)


async def test_topic_room_manager_redis_publish_fallback() -> None:
    redis = MagicMock()
    redis.publish = AsyncMock(side_effect=RuntimeError("down"))
    mgr = TopicRoomManager(redis, REDIS_CHANNEL_PREFIX_CHAT)
    room_id = uuid.uuid4()
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    with patch.object(mgr, "_subscribe", new_callable=AsyncMock):
        await mgr.connect(room_id, ws)
    await mgr.publish(room_id, {"a": 1})
    ws.send_text.assert_awaited()


async def test_has_connections_multitab() -> None:
    mgr = im_mod.InboxManager(redis=None)
    assert mgr.has_connections("u1") is False
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    await mgr.connect("u1", ws1)
    await mgr.connect("u1", ws2)
    assert mgr.has_connections("u1") is True
    mgr.disconnect("u1", ws1)
    assert mgr.has_connections("u1") is True
    mgr.disconnect("u1", ws2)
    assert mgr.has_connections("u1") is False


async def test_publish_presence_broadcasts_locally_without_redis() -> None:
    mgr = im_mod.InboxManager(redis=None)
    ws_a = AsyncMock()
    ws_a.accept = AsyncMock()
    ws_a.send_text = AsyncMock()
    ws_b = AsyncMock()
    ws_b.accept = AsyncMock()
    ws_b.send_text = AsyncMock()
    await mgr.connect("u_alice", ws_a)
    await mgr.connect("u_bob", ws_b)
    await mgr.publish_presence({"event": "presence_update", "sub": "u_alice", "status": "offline"})
    ws_a.send_text.assert_awaited_once()
    ws_b.send_text.assert_awaited_once()


async def test_publish_presence_falls_back_to_local_on_redis_error() -> None:
    redis = MagicMock()
    redis.publish = AsyncMock(side_effect=RuntimeError("redis down"))
    mgr = im_mod.InboxManager(redis=redis)
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    mgr._local["u1"].add(ws)
    await mgr.publish_presence({"event": "presence_update", "sub": "u1", "status": "offline"})
    redis.publish.assert_awaited_once()
    ws.send_text.assert_awaited_once()


async def test_topic_room_disconnect_user_closes_matching_socket() -> None:
    mgr = TopicRoomManager(redis=None, channel_prefix=REDIS_CHANNEL_PREFIX_CHAT)
    room_id = uuid.uuid4()
    keep = AsyncMock()
    keep.accept = AsyncMock()
    drop = AsyncMock()
    drop.accept = AsyncMock()
    drop.close = AsyncMock()
    await mgr.connect(room_id, keep, user_sub="keep-sub")
    await mgr.connect(room_id, drop, user_sub="kick-sub")
    await mgr.disconnect_user(room_id, "kick-sub")
    assert drop not in mgr._local.get(room_id, set())
    assert keep in mgr._local[room_id]
    drop.close.assert_awaited_once()


async def test_inbox_manager_disconnect_cancels_redis_sub_task() -> None:
    redis = MagicMock()

    async def _fake_subscribe(_self: object, user_sub: str) -> None:
        await asyncio.sleep(100)

    with patch.object(im_mod.InboxManager, "_subscribe", new=_fake_subscribe):
        mgr = im_mod.InboxManager(redis=redis)
        ws = AsyncMock()
        ws.accept = AsyncMock()
        await mgr.connect("long-user-sub-for-test", ws)
        mgr.disconnect("long-user-sub-for-test", ws)
        await asyncio.sleep(0.01)
        task = mgr._sub_tasks.get("long-user-sub-for-test")
        assert task is None or task.cancelled()
