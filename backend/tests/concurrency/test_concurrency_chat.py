"""Гонки чатов: DM, участник группы, web-push, hide, pin/emoji-лимиты."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.core.exceptions import ConflictError, ValidationError
from app.core.utils import now_utc
from app.infrastructure.db.models.portal_chat import (
    PortalChat,
    PortalChatMember,
    PortalChatMessage,
    PortalChatMessageHidden,
    PortalChatMessageReaction,
)
from app.infrastructure.db.models.portal_web_push import PortalWebPushSubscription
from app.portal_chat.constants import CHAT_PINNED_MESSAGES_MAX_PER_CHAT
from app.portal_chat.services._mutations import delete_message_for_user
from app.portal_chat.services._mutations_chats import get_or_create_direct_chat
from app.portal_chat.services._mutations_pin import pin_message
from app.portal_chat.services._mutations_reactions import toggle_message_reaction
from app.portal_chat.services.group_chat import add_member_to_group_chat
from app.portal_chat.services.web_push import upsert_push_subscription
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.concurrency.conftest import profile_from_user
from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b


@pytest.mark.asyncio
async def test_parallel_get_or_create_direct_chat_one_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    async with sqlite_concurrency_factory() as s:
        s.add(profile_from_user(admin))
        s.add(profile_from_user(other))
        await s.commit()

    chats: list[PortalChat] = []

    async def try_create() -> None:
        async with sqlite_concurrency_factory() as sess:
            chats.append(await get_or_create_direct_chat(sess, admin, other.sub))

    await asyncio.gather(try_create(), try_create())

    assert len(chats) == 2
    assert chats[0].id == chats[1].id
    key = "|".join(sorted([admin.sub, other.sub]))
    async with sqlite_concurrency_factory() as s:
        n = await s.execute(select(func.count()).select_from(PortalChat).where(PortalChat.canonical_dm_key == key))
        assert n.scalar_one() == 1


@pytest.mark.asyncio
async def test_parallel_add_member_to_group_chat_one_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.portal_chat.services.group_chat.publish_chat_list_refresh", AsyncMock())
    manager = MagicMock()
    manager.publish = AsyncMock()
    monkeypatch.setattr("app.portal_chat.services.group_chat.get_chat_manager", lambda: manager)

    owner = user_portal_admin()
    member = user_portal_regular()
    guest = user_portal_user_b()
    chat_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add_all([profile_from_user(owner), profile_from_user(member), profile_from_user(guest)])
        s.add(PortalChat(id=chat_id, title="Группа", created_by_sub=owner.sub))
        s.add(PortalChatMember(chat_id=chat_id, user_sub=owner.sub))
        s.add(PortalChatMember(chat_id=chat_id, user_sub=member.sub))
        await s.commit()

    outcomes: list[str] = []

    async def try_add() -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await add_member_to_group_chat(sess, owner, chat_id, new_member_sub=guest.sub)
                outcomes.append("ok")
            except ConflictError:
                outcomes.append("conflict")

    await asyncio.gather(try_add(), try_add())
    assert sorted(outcomes) == ["conflict", "ok"]

    async with sqlite_concurrency_factory() as s:
        n = await s.execute(
            select(func.count())
            .select_from(PortalChatMember)
            .where(PortalChatMember.chat_id == chat_id, PortalChatMember.user_sub == guest.sub)
        )
        assert n.scalar_one() == 1


@pytest.mark.asyncio
async def test_parallel_upsert_push_subscription_one_endpoint(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    user = user_portal_regular()
    payload = {
        "endpoint": "https://push.example/ep-1",
        "keys": {"p256dh": "dGVzdC1wMjU2ZGg", "auth": "dGVzdC1hdXRo"},
    }

    async def try_upsert() -> None:
        async with sqlite_concurrency_factory() as sess:
            await upsert_push_subscription(sess, user, payload)

    await asyncio.gather(try_upsert(), try_upsert())

    async with sqlite_concurrency_factory() as s:
        n = await s.execute(
            select(func.count())
            .select_from(PortalWebPushSubscription)
            .where(PortalWebPushSubscription.endpoint == payload["endpoint"])
        )
        assert n.scalar_one() == 1


async def _seed_group(
    factory: async_sessionmaker[AsyncSession],
    owner_sub: str,
    member_subs: list[str],
) -> uuid.UUID:
    chat_id = uuid.uuid4()
    async with factory() as s:
        s.add(PortalChat(id=chat_id, title="Гонка", created_by_sub=owner_sub))
        s.add(PortalChatMember(chat_id=chat_id, user_sub=owner_sub))
        for sub in member_subs:
            s.add(PortalChatMember(chat_id=chat_id, user_sub=sub))
        await s.commit()
    return chat_id


@pytest.mark.asyncio
async def test_parallel_hide_message_one_hidden_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    owner = user_portal_admin()
    peer = user_portal_regular()
    async with sqlite_concurrency_factory() as s:
        s.add_all([profile_from_user(owner), profile_from_user(peer)])
        await s.commit()
    chat_id = await _seed_group(sqlite_concurrency_factory, owner.sub, [peer.sub])
    msg_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(PortalChatMessage(id=msg_id, chat_id=chat_id, author_sub=owner.sub, body="hide"))
        await s.commit()

    async def try_hide() -> None:
        async with sqlite_concurrency_factory() as sess:
            await delete_message_for_user(sess, owner, chat_id, msg_id)

    await asyncio.gather(try_hide(), try_hide())
    async with sqlite_concurrency_factory() as s:
        n = await s.execute(
            select(func.count())
            .select_from(PortalChatMessageHidden)
            .where(
                PortalChatMessageHidden.message_id == msg_id,
                PortalChatMessageHidden.user_sub == owner.sub,
            )
        )
        assert n.scalar_one() == 1


@pytest.mark.asyncio
async def test_parallel_new_emoji_respects_unique_limit(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.portal_chat.services._mutations_reactions.get_chat_manager",
        lambda: MagicMock(publish=AsyncMock()),
    )
    owner = user_portal_admin()
    peer = user_portal_regular()
    async with sqlite_concurrency_factory() as s:
        s.add_all([profile_from_user(owner), profile_from_user(peer)])
        await s.commit()
    chat_id = await _seed_group(sqlite_concurrency_factory, owner.sub, [peer.sub])
    msg_id = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        s.add(PortalChatMessage(id=msg_id, chat_id=chat_id, author_sub=owner.sub, body="rx"))
        s.add(PortalChatMessageReaction(message_id=msg_id, user_sub=owner.sub, emoji="👍"))
        s.add(PortalChatMessageReaction(message_id=msg_id, user_sub=peer.sub, emoji="❤️"))
        await s.commit()

    outcomes: list[str] = []

    async def try_react(user: object, emoji: str) -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await toggle_message_reaction(sess, user, chat_id, msg_id, emoji)
                outcomes.append("ok")
            except ValidationError:
                outcomes.append("limit")

    await asyncio.gather(try_react(owner, "🎉"), try_react(peer, "🔥"))
    assert sorted(outcomes) == ["limit", "ok"]
    async with sqlite_concurrency_factory() as s:
        n = await s.execute(
            select(func.count(PortalChatMessageReaction.emoji.distinct())).where(
                PortalChatMessageReaction.message_id == msg_id
            )
        )
        assert n.scalar_one() == 3


@pytest.mark.asyncio
async def test_parallel_pin_respects_chat_limit(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.portal_chat.services._mutations_pin.get_chat_manager",
        lambda: MagicMock(publish=AsyncMock()),
    )
    owner = user_portal_admin()
    peer = user_portal_regular()
    async with sqlite_concurrency_factory() as s:
        s.add_all([profile_from_user(owner), profile_from_user(peer)])
        await s.commit()
    chat_id = await _seed_group(sqlite_concurrency_factory, owner.sub, [peer.sub])
    already = CHAT_PINNED_MESSAGES_MAX_PER_CHAT - 1
    extra_a = uuid.uuid4()
    extra_b = uuid.uuid4()
    async with sqlite_concurrency_factory() as s:
        now = now_utc()
        for i in range(already):
            s.add(
                PortalChatMessage(
                    id=uuid.uuid4(),
                    chat_id=chat_id,
                    author_sub=owner.sub,
                    body=f"p{i}",
                    pinned_at=now,
                    pinned_by_sub=owner.sub,
                )
            )
        s.add(PortalChatMessage(id=extra_a, chat_id=chat_id, author_sub=owner.sub, body="new-a"))
        s.add(PortalChatMessage(id=extra_b, chat_id=chat_id, author_sub=peer.sub, body="new-b"))
        await s.commit()

    outcomes: list[str] = []

    async def try_pin(user: object, mid: uuid.UUID) -> None:
        async with sqlite_concurrency_factory() as sess:
            try:
                await pin_message(sess, user, chat_id, mid)
                outcomes.append("ok")
            except ValidationError:
                outcomes.append("limit")

    await asyncio.gather(try_pin(owner, extra_a), try_pin(peer, extra_b))
    assert sorted(outcomes) == ["limit", "ok"]
    async with sqlite_concurrency_factory() as s:
        n = await s.execute(
            select(func.count())
            .select_from(PortalChatMessage)
            .where(PortalChatMessage.chat_id == chat_id, PortalChatMessage.pinned_at.is_not(None))
        )
        assert n.scalar_one() == CHAT_PINNED_MESSAGES_MAX_PER_CHAT
