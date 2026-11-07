"""Юнит-тесты пересылки сообщений (forward_chat_message)."""

from __future__ import annotations

import io
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.infrastructure.db.models.portal_chat import PortalChatAttachment
from app.portal_chat.schemas.chat import PortalChatMessageCreate
from app.portal_chat.services import attachment as att_svc
from app.portal_chat.services import chat as chat_svc
from app.portal_chat.services._mutations import delete_message_for_all, delete_message_for_user
from app.portal_chat.services._mutations_forward import forward_chat_message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import (
    user_portal_admin,
    user_portal_manager,
    user_portal_regular,
    user_portal_user_b,
)


@pytest.fixture(autouse=True)
def _mock_forward_side_effects() -> object:
    mgr = MagicMock(publish=AsyncMock())
    with (
        patch("app.infrastructure.ws.managers.get_chat_manager", return_value=mgr),
        patch("app.portal_chat.services.inbox_publish.publish_chat_list_refresh", new_callable=AsyncMock),
    ):
        yield


async def test_forward_text_message_to_other_chat_success(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat_a = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, regular.sub)
    chat_b = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_user_b().sub)

    src = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat_a.id,
        PortalChatMessageCreate(body="текст для пересылки"),
    )
    mid = src.id

    new_msg = await forward_chat_message(
        sqlite_session,
        admin,
        target_chat_id=chat_b.id,
        from_chat_id=chat_a.id,
        message_id=mid,
    )

    assert new_msg.chat_id == chat_b.id
    assert new_msg.body == "текст для пересылки"
    assert new_msg.author_sub == admin.sub
    assert new_msg.forwarded_from_message_id == mid
    assert new_msg.forwarded_from_author_sub == admin.sub

    chat_b_refreshed = await sqlite_session.get(type(chat_b), chat_b.id)
    assert chat_b_refreshed is not None
    assert chat_b_refreshed.updated_at is not None


async def test_forward_message_with_attachments_copies_storage(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat_a = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, regular.sub)
    chat_b = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_user_b().sub)

    with patch(
        "app.portal_chat.services.attachment.async_upload_file", new_callable=AsyncMock, return_value="orig-key-1"
    ):
        att = await att_svc.upload_attachment(
            sqlite_session,
            file_data=io.BytesIO(b"x"),
            file_size=1,
            content_type="text/plain",
            original_filename="a.txt",
            uploader_sub=admin.sub,
            chat_id=chat_a.id,
        )
    src = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat_a.id,
        PortalChatMessageCreate(body="с файлом", attachment_ids=[att.id]),
    )

    copy_mock = AsyncMock(return_value="new-key-a")
    with patch("app.portal_chat.services._mutations_forward.async_copy_object_to_new_key", copy_mock):
        new_msg = await forward_chat_message(
            sqlite_session,
            admin,
            target_chat_id=chat_b.id,
            from_chat_id=chat_a.id,
            message_id=src.id,
        )

    copy_mock.assert_called_once_with("orig-key-1")
    stmt = select(PortalChatAttachment).where(
        PortalChatAttachment.message_id == new_msg.id,
        PortalChatAttachment.chat_id == chat_b.id,
    )
    linked = list((await sqlite_session.execute(stmt)).scalars().all())
    assert len(linked) == 1
    assert linked[0].storage_key == "new-key-a"
    assert linked[0].uploader_sub == admin.sub


async def test_forward_to_same_chat_raises_validation(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="x"),
    )
    with pytest.raises(ValidationError, match="другой чат"):
        await forward_chat_message(
            sqlite_session,
            admin,
            target_chat_id=chat.id,
            from_chat_id=chat.id,
            message_id=msg.id,
        )


async def test_forward_message_not_found(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat_a = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    chat_b = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_user_b().sub)
    fake_id = uuid.uuid4()
    with pytest.raises(NotFoundError, match="Сообщение не найдено"):
        await forward_chat_message(
            sqlite_session,
            admin,
            target_chat_id=chat_b.id,
            from_chat_id=chat_a.id,
            message_id=fake_id,
        )


async def test_forward_message_from_wrong_chat_returns_not_found(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat_a = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    chat_b = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_user_b().sub)
    chat_c = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_manager().sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat_a.id,
        PortalChatMessageCreate(body="только в A"),
    )
    with pytest.raises(NotFoundError, match="Сообщение не найдено"):
        await forward_chat_message(
            sqlite_session,
            admin,
            target_chat_id=chat_b.id,
            from_chat_id=chat_c.id,
            message_id=msg.id,
        )


async def test_forward_deleted_message_raises_validation(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    chat_a = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    chat_b = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_user_b().sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat_a.id,
        PortalChatMessageCreate(body="удалить"),
    )
    mid = msg.id
    msg.__dict__.pop("attachments", None)
    await sqlite_session.refresh(msg)
    with patch("app.portal_chat.services._mutations.async_delete_object", new_callable=AsyncMock):
        await delete_message_for_all(sqlite_session, admin, chat_a.id, mid)

    with pytest.raises(ValidationError, match="удалённое"):
        await forward_chat_message(
            sqlite_session,
            admin,
            target_chat_id=chat_b.id,
            from_chat_id=chat_a.id,
            message_id=mid,
        )


async def test_forward_hidden_for_user_message_raises_validation(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    chat_a = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    chat_b = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_user_b().sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat_a.id,
        PortalChatMessageCreate(body="скрыть у меня"),
    )
    await delete_message_for_user(sqlite_session, admin, chat_a.id, msg.id)

    with pytest.raises(ValidationError, match="Нельзя переслать это сообщение"):
        await forward_chat_message(
            sqlite_session,
            admin,
            target_chat_id=chat_b.id,
            from_chat_id=chat_a.id,
            message_id=msg.id,
        )


async def test_forward_to_chat_without_access_forbidden(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    outsider = user_portal_user_b()
    chat_a = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    chat_b_only = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_manager().sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat_a.id,
        PortalChatMessageCreate(body="секрет"),
    )
    with pytest.raises(ForbiddenError, match="Нет доступа к чату"):
        await forward_chat_message(
            sqlite_session,
            outsider,
            target_chat_id=chat_b_only.id,
            from_chat_id=chat_a.id,
            message_id=msg.id,
        )


async def test_forward_preserves_original_author_for_chained_forward(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat_a = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, regular.sub)
    chat_b = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_user_b().sub)
    chat_c = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_manager().sub)

    src = await chat_svc.post_message(
        sqlite_session,
        regular,
        chat_a.id,
        PortalChatMessageCreate(body="оригинал"),
    )

    with patch(
        "app.portal_chat.services._mutations_forward.async_copy_object_to_new_key",
        new_callable=AsyncMock,
        return_value="k",
    ):
        first = await forward_chat_message(
            sqlite_session,
            admin,
            target_chat_id=chat_b.id,
            from_chat_id=chat_a.id,
            message_id=src.id,
        )
        second = await forward_chat_message(
            sqlite_session,
            admin,
            target_chat_id=chat_c.id,
            from_chat_id=chat_b.id,
            message_id=first.id,
        )

    assert first.forwarded_from_author_sub == regular.sub
    assert second.forwarded_from_author_sub == regular.sub
    assert second.body == "оригинал"
