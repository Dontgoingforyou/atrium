"""Нормализация mentions при отправке сообщений в чат."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.portal_chat.schemas.chat import PortalChatCreate, PortalChatMessageCreate
from app.portal_chat.services import chat as chat_svc
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b


@pytest.fixture(autouse=True)
def _mock_chat_and_inbox_publish() -> object:
    mgr = MagicMock(publish=AsyncMock())
    with (
        patch("app.infrastructure.ws.managers.get_chat_manager", return_value=mgr),
        patch("app.infrastructure.ws.inbox_manager.get_inbox_manager", return_value=mgr),
    ):
        yield


def test_portal_chat_message_create_rejects_more_than_32_mentions() -> None:
    with pytest.raises(ValidationError):
        PortalChatMessageCreate(
            body="x",
            mentions=[f"sub-{i}" for i in range(33)],
        )


async def test_post_message_mentions_group_keeps_members_only_order_dedup(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    member = user_portal_regular()
    outsider = user_portal_user_b()
    group = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Команда", member_subs=[member.sub]),
    )
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        group.id,
        PortalChatMessageCreate(
            body="привет",
            mentions=[
                member.sub,
                member.sub,
                outsider.sub,
                admin.sub,
            ],
        ),
    )
    assert msg.mentions == [member.sub]


async def test_post_message_mentions_dm_excludes_author(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    peer = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, peer.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(
            body="ЛС",
            mentions=[peer.sub, admin.sub],
        ),
    )
    assert msg.mentions == [peer.sub]
