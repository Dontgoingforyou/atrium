"""Юнит-тесты реакций на сообщения (toggle_message_reaction)."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.infrastructure.db.models.portal_chat import PortalChatMessage, PortalChatMessageReaction
from app.portal_chat.schemas.chat import PortalChatMessageCreate
from app.portal_chat.services import chat as chat_svc
from app.portal_chat.services._mutations_reactions import toggle_message_reaction
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b


def _detach_post_message_instrumentation(msg: object) -> None:
    """post_message / toggle кладут ``attachments`` в ``__dict__`` — иначе ``refresh`` ломает ORM."""
    msg.__dict__.pop("attachments", None)  # type: ignore[attr-defined]


async def _toggle_reaction(
    session: AsyncSession,
    user: object,
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    emoji: str,
) -> object:
    row = await session.get(PortalChatMessage, message_id)
    assert row is not None
    _detach_post_message_instrumentation(row)
    return await toggle_message_reaction(session, user, chat_id, message_id, emoji)


@pytest.fixture(autouse=True)
def _mock_reaction_ws_publish() -> object:
    mgr = MagicMock(publish=AsyncMock())
    with patch("app.infrastructure.ws.managers.get_chat_manager", return_value=mgr):
        yield


async def _count_reactions(session: AsyncSession, message_id: uuid.UUID) -> int:
    q = (
        select(func.count())
        .select_from(PortalChatMessageReaction)
        .where(PortalChatMessageReaction.message_id == message_id)
    )
    return int((await session.execute(q)).scalar_one())


async def test_toggle_adds_reaction_first_time(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, regular.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="текст"),
    )
    out = await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, "👍")
    assert out.id == msg.id
    assert await _count_reactions(sqlite_session, msg.id) == 1


async def test_toggle_removes_existing_reaction_for_same_user(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="x"),
    )
    await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, "👍")
    assert await _count_reactions(sqlite_session, msg.id) == 1
    await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, "👍")
    assert await _count_reactions(sqlite_session, msg.id) == 0


async def test_toggle_keeps_others_reaction_when_user_removes_own(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, regular.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="общее"),
    )
    await _toggle_reaction(sqlite_session, regular, chat.id, msg.id, "👍")
    await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, "👍")
    assert await _count_reactions(sqlite_session, msg.id) == 2
    await _toggle_reaction(sqlite_session, regular, chat.id, msg.id, "👍")
    assert await _count_reactions(sqlite_session, msg.id) == 1
    row = (
        await sqlite_session.execute(
            select(PortalChatMessageReaction).where(
                PortalChatMessageReaction.message_id == msg.id,
                PortalChatMessageReaction.emoji == "👍",
            )
        )
    ).scalar_one()
    assert row.user_sub == admin.sub


async def test_toggle_reaction_message_not_in_chat_raises_not_found(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat_a = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    chat_b = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_user_b().sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat_a.id,
        PortalChatMessageCreate(body="только в A"),
    )
    with pytest.raises(NotFoundError, match="Сообщение не найдено"):
        await _toggle_reaction(sqlite_session, admin, chat_b.id, msg.id, "👍")


async def test_toggle_reaction_empty_after_strip_raises_validation(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="y"),
    )
    with pytest.raises(ValidationError, match="Некорректная реакция"):
        await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, "   ")


@pytest.mark.parametrize(
    "fourth_emoji",
    ["🔥", "⭐"],
)
async def test_toggle_reaction_limit_three_unique_emojis(
    sqlite_session: AsyncSession,
    fourth_emoji: str,
) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="лимит"),
    )
    await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, "👍")
    await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, "❤️")
    await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, "🎉")
    with pytest.raises(ValidationError, match="3 уникальных"):
        await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, fourth_emoji)


async def test_toggle_allows_joining_existing_emoji_when_three_unique_already(
    sqlite_session: AsyncSession,
) -> None:
    """Лимит 3 уникальных не мешает другому пользователю поставить уже существующую реакцию."""
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, regular.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="три типа"),
    )
    await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, "❤️")
    await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, "🔥")
    await _toggle_reaction(sqlite_session, admin, chat.id, msg.id, "😍")
    assert await _count_reactions(sqlite_session, msg.id) == 3

    await _toggle_reaction(sqlite_session, regular, chat.id, msg.id, "🔥")
    assert await _count_reactions(sqlite_session, msg.id) == 4
    rows = (
        (
            await sqlite_session.execute(
                select(PortalChatMessageReaction).where(
                    PortalChatMessageReaction.message_id == msg.id,
                    PortalChatMessageReaction.emoji == "🔥",
                )
            )
        )
        .scalars()
        .all()
    )
    assert {r.user_sub for r in rows} == {admin.sub, regular.sub}


async def test_toggle_reaction_non_member_forbidden(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    outsider = user_portal_user_b()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="закрыто"),
    )
    with pytest.raises(ForbiddenError, match="Нет доступа к чату"):
        await _toggle_reaction(sqlite_session, outsider, chat.id, msg.id, "👍")
