"""Удаление чата целиком: права и MinIO."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.exceptions import ForbiddenError, NotFoundError
from app.infrastructure.db.models.portal_chat import PortalChat, PortalChatAttachment, PortalChatMember
from app.portal_chat.schemas.chat import PortalChatCreate
from app.portal_chat.services import chat as chat_svc
from app.portal_chat.services.delete_chat import delete_entire_chat
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b


@pytest.fixture
def _mock_delete_side() -> object:
    mgr = MagicMock(publish=AsyncMock(), disconnect_user=AsyncMock())
    with (
        patch("app.portal_chat.services.delete_chat.async_delete_objects", new_callable=AsyncMock) as dm,
        patch("app.portal_chat.services.delete_chat.get_chat_manager", return_value=mgr),
        patch("app.portal_chat.services.delete_chat.publish_chat_list_refresh", new_callable=AsyncMock),
        patch(
            "app.portal_chat.services.delete_chat.delete_embeddings_batch",
            new_callable=AsyncMock,
        ) as emb_del,
    ):
        yield dm, emb_del


@pytest.mark.asyncio
async def test_delete_group_non_creator_forbidden(
    sqlite_session: AsyncSession,
    _mock_delete_side: MagicMock,
) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Гр", member_subs=[regular.sub]),
    )
    with pytest.raises(ForbiddenError, match="создатель"):
        await delete_entire_chat(sqlite_session, regular, chat.id)


@pytest.mark.asyncio
async def test_delete_dm_success_removes_row(
    sqlite_session: AsyncSession,
    _mock_delete_side: tuple[MagicMock, AsyncMock],
) -> None:
    admin = user_portal_admin()
    peer = user_portal_user_b()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, peer.sub)
    cid = chat.id

    dm_mock, emb_mock = _mock_delete_side
    await delete_entire_chat(sqlite_session, admin, cid)

    assert dm_mock.call_count <= 1
    emb_mock.assert_awaited_once()
    assert emb_mock.await_args[0][1] == "chat_message"
    assert await sqlite_session.get(PortalChat, cid) is None


@pytest.mark.asyncio
async def test_delete_dm_peer_can_delete(
    sqlite_session: AsyncSession,
    _mock_delete_side: tuple[MagicMock, AsyncMock],
) -> None:
    admin = user_portal_admin()
    peer = user_portal_user_b()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, peer.sub)
    cid = chat.id

    await delete_entire_chat(sqlite_session, peer, cid)

    assert await sqlite_session.get(PortalChat, cid) is None


@pytest.mark.asyncio
async def test_delete_group_creator_success_deletes_avatar_key(
    sqlite_session: AsyncSession,
    _mock_delete_side: tuple[MagicMock, AsyncMock],
) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="А", member_subs=[regular.sub]),
    )
    chat.avatar_storage_key = "avatars/chats/g/face.jpg"
    await sqlite_session.commit()
    cid = chat.id

    await delete_entire_chat(sqlite_session, admin, cid)

    dm_mock, _ = _mock_delete_side
    keys = list(dm_mock.call_args[0][0])
    assert "avatars/chats/g/face.jpg" in keys
    assert await sqlite_session.get(PortalChat, cid) is None


@pytest.mark.asyncio
async def test_delete_group_with_attachment_keys(
    sqlite_session: AsyncSession,
    _mock_delete_side: tuple[MagicMock, AsyncMock],
) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="В", member_subs=[regular.sub]),
    )
    from datetime import UTC, datetime

    from app.infrastructure.db.models.portal_chat import PortalChatMessage

    now = datetime.now(UTC)
    msg = PortalChatMessage(
        id=__import__("uuid").uuid4(),
        chat_id=chat.id,
        author_sub=admin.sub,
        body="x",
        created_at=now,
    )
    sqlite_session.add(msg)
    await sqlite_session.flush()
    sqlite_session.add(
        PortalChatAttachment(
            id=__import__("uuid").uuid4(),
            message_id=msg.id,
            chat_id=chat.id,
            uploader_sub=admin.sub,
            original_filename="f.bin",
            content_type="application/octet-stream",
            file_size=1,
            storage_key="attachments/chat/att1",
            created_at=now,
        )
    )
    await sqlite_session.commit()
    cid = chat.id

    await delete_entire_chat(sqlite_session, admin, cid)

    dm_mock, _ = _mock_delete_side
    keys = list(dm_mock.call_args[0][0])
    assert "attachments/chat/att1" in keys


@pytest.mark.asyncio
async def test_delete_chat_outsider_not_found(
    sqlite_session: AsyncSession,
    _mock_delete_side: MagicMock,
) -> None:
    admin = user_portal_admin()
    outsider = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Закрыто", member_subs=[user_portal_user_b().sub]),
    )
    with pytest.raises(NotFoundError):
        await delete_entire_chat(sqlite_session, outsider, chat.id)


@pytest.mark.asyncio
async def test_delete_dm_publishes_chat_deleted_after_commit(
    sqlite_session: AsyncSession,
) -> None:
    """WS-событие "chat_deleted" должно уходить ПОСЛЕ коммита удаления, а не до."""
    admin = user_portal_admin()
    peer = user_portal_user_b()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, peer.sub)
    cid = chat.id

    captured: dict[str, bool] = {}

    async def _capture_publish(_chat_id: object, _payload: object) -> None:
        captured["already_committed"] = await sqlite_session.get(PortalChat, cid) is None

    mgr = MagicMock(publish=AsyncMock(side_effect=_capture_publish), disconnect_user=AsyncMock())
    with (
        patch("app.portal_chat.services.delete_chat.async_delete_objects", new_callable=AsyncMock),
        patch("app.portal_chat.services.delete_chat.get_chat_manager", return_value=mgr),
        patch("app.portal_chat.services.delete_chat.publish_chat_list_refresh", new_callable=AsyncMock),
        patch("app.portal_chat.services.delete_chat.delete_embeddings_batch", new_callable=AsyncMock),
    ):
        await delete_entire_chat(sqlite_session, admin, cid)

    mgr.publish.assert_awaited_once()
    assert captured["already_committed"] is True


@pytest.mark.asyncio
async def test_delete_after_delete_members_gone(
    sqlite_session: AsyncSession,
    _mock_delete_side: MagicMock,
) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Каскад", member_subs=[regular.sub]),
    )
    cid = chat.id
    await delete_entire_chat(sqlite_session, admin, cid)

    q = select(PortalChatMember).where(PortalChatMember.chat_id == cid)
    assert list((await sqlite_session.execute(q)).scalars().all()) == []
