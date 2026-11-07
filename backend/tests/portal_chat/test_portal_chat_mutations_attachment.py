"""Тесты мутаций portal_chat и модуля attachment (MinIO моки)."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.exceptions import ForbiddenError, NotFoundError, StorageUnavailableError, ValidationError
from app.infrastructure.db.models.portal_chat import PortalChatAttachment, PortalChatMessage
from app.portal_chat.schemas.chat import PortalChatCreate, PortalChatMessageCreate, PortalChatMessageUpdate
from app.portal_chat.services import attachment as att_svc
from app.portal_chat.services import chat as chat_svc
from app.portal_chat.services._mutations import (
    delete_message_for_all,
    delete_message_for_user,
    update_message,
)
from app.portal_chat.services._mutations_chats import create_chat
from minio.error import S3Error
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b


@pytest.fixture(autouse=True)
def _mock_chat_and_inbox_publish() -> object:
    """post_message / delete_* вызывают WS-публикацию — без реального Redis."""
    mgr = MagicMock(publish=AsyncMock())
    with (
        patch("app.infrastructure.ws.managers.get_chat_manager", return_value=mgr),
        patch("app.infrastructure.ws.inbox_manager.get_inbox_manager", return_value=mgr),
    ):
        yield


@pytest.fixture
def mock_delete_object_ok() -> AsyncMock:
    m = AsyncMock(return_value=None)
    with patch("app.portal_chat.services._mutations.async_delete_object", m):
        yield m


@pytest.mark.asyncio
async def test_delete_message_for_all_withdraws_inbox_and_post_carries_message_id(
    sqlite_session: AsyncSession,
    mock_delete_object_ok: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Новое сообщение несёт message_id; удаление для всех отзывает инбокс у остальных."""
    admin = user_portal_admin()
    other = user_portal_regular()
    refreshes: list[dict[str, object]] = []
    withdrawals: list[tuple[list[str], uuid.UUID, uuid.UUID]] = []

    async def _refresh(*_args: object, **kwargs: object) -> None:
        refreshes.append(kwargs)

    async def _withdraw(subs: list[str], chat_id: uuid.UUID, message_id: uuid.UUID) -> None:
        withdrawals.append((list(subs), chat_id, message_id))

    monkeypatch.setattr("app.portal_chat.services._mutations.publish_chat_list_refresh", _refresh)
    monkeypatch.setattr("app.portal_chat.services._mutations.publish_chat_inbox_withdrawals", _withdraw)

    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="будет удалено"),
    )
    assert refreshes
    assert refreshes[0].get("message_id") == msg.id

    msg.__dict__.pop("attachments", None)
    await sqlite_session.refresh(msg)
    await delete_message_for_all(sqlite_session, admin, chat.id, msg.id)
    assert withdrawals == [([other.sub], chat.id, msg.id)]


@pytest.mark.asyncio
async def test_delete_message_for_user_does_not_withdraw_inbox(
    sqlite_session: AsyncSession,
    mock_delete_object_ok: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    called: list[int] = []

    async def _withdraw(*_args: object, **_kwargs: object) -> None:
        called.append(1)

    monkeypatch.setattr("app.portal_chat.services._mutations.publish_chat_inbox_withdrawals", _withdraw)
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="скрыть у себя"),
    )
    await delete_message_for_user(sqlite_session, other, chat.id, msg.id)
    assert called == []


@pytest.mark.asyncio
async def test_delete_message_for_user_idempotent(
    sqlite_session: AsyncSession,
    mock_delete_object_ok: MagicMock,
) -> None:
    """Повторное «удалить у меня» не падает."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="x"),
    )
    await delete_message_for_user(sqlite_session, other, chat.id, msg.id)
    await delete_message_for_user(sqlite_session, other, chat.id, msg.id)


async def test_delete_message_for_all_already_deleted_short_circuit(
    sqlite_session: AsyncSession,
    mock_delete_object_ok: MagicMock,
) -> None:
    """Повторный delete for all при уже удалённом сообщении — без повторного MinIO."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="удалить"),
    )
    mid = msg.id
    msg.__dict__.pop("attachments", None)
    await sqlite_session.refresh(msg)
    m1 = AsyncMock(return_value=None)
    with patch("app.portal_chat.services._mutations.async_delete_object", m1):
        await delete_message_for_all(sqlite_session, admin, chat.id, mid)
    m1.assert_not_called()
    row = await sqlite_session.get(PortalChatMessage, mid)
    assert row is not None
    assert row.deleted_for_all_at is not None

    m2 = AsyncMock(return_value=None)
    with patch("app.portal_chat.services._mutations.async_delete_object", m2):
        out = await delete_message_for_all(sqlite_session, admin, chat.id, mid)
    m2.assert_not_called()
    assert out.deleted_for_all_at is not None


async def test_delete_message_for_all_minio_failure_raises_storage_unavailable(
    sqlite_session: AsyncSession,
) -> None:
    """S3Error при purge вложений → StorageUnavailableError."""

    def _raise(*_a: object, **_k: object) -> None:
        raise S3Error(MagicMock(), "InternalError", "fail", "r", "1", "h")

    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="текст"),
    )
    msg.__dict__.pop("attachments", None)
    await sqlite_session.refresh(msg)
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub=admin.sub,
        original_filename="f",
        content_type="application/octet-stream",
        file_size=2,
        storage_key="key-s3",
        message_id=msg.id,
    )
    sqlite_session.add(att)
    await sqlite_session.commit()
    mid = msg.id

    with patch("app.portal_chat.services._mutations.async_delete_object", new_callable=AsyncMock, side_effect=_raise):
        with pytest.raises(StorageUnavailableError):
            await delete_message_for_all(sqlite_session, admin, chat.id, mid)


async def test_upload_attachment_zero_size_validation(
    sqlite_session: AsyncSession,
) -> None:
    """Нулевой размер файла — ValidationError."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    with pytest.raises(ValidationError, match="Размер файла"):
        await att_svc.upload_attachment(
            sqlite_session,
            file_data=io.BytesIO(b""),
            file_size=0,
            content_type="text/plain",
            original_filename="empty.txt",
            uploader_sub=admin.sub,
            chat_id=chat.id,
        )


async def test_upload_attachment_too_large(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Превышение лимита — ValidationError."""
    from app.portal_chat.services import attachment as att_mod

    fake = MagicMock()
    fake.attachment_max_size_bytes = 100
    monkeypatch.setattr(att_mod, "get_settings", lambda: fake)
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    with pytest.raises(ValidationError, match="Размер файла"):
        await att_svc.upload_attachment(
            sqlite_session,
            file_data=io.BytesIO(b"x" * 200),
            file_size=200,
            content_type="text/plain",
            original_filename="big.bin",
            uploader_sub=admin.sub,
            chat_id=chat.id,
        )


async def test_link_attachments_not_found(
    sqlite_session: AsyncSession,
) -> None:
    with pytest.raises(NotFoundError, match="не найдено"):
        await att_svc.link_attachments_to_message(
            sqlite_session,
            attachment_ids=[uuid.uuid4()],
            message_id=uuid.uuid4(),
            chat_id=uuid.uuid4(),
            uploader_sub="x",
        )


async def test_link_attachments_wrong_chat(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    user_b = user_portal_user_b()
    chat_a = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_b.sub)

    with patch("app.portal_chat.services.attachment.async_upload_file", new_callable=AsyncMock, return_value="sk"):
        att = await att_svc.upload_attachment(
            sqlite_session,
            file_data=io.BytesIO(b"1"),
            file_size=1,
            content_type="text/plain",
            original_filename="a.txt",
            uploader_sub=admin.sub,
            chat_id=chat_a.id,
        )

    msg_id = uuid.uuid4()
    wrong_chat = uuid.uuid4()
    with pytest.raises(ForbiddenError, match="другому чату"):
        await att_svc.link_attachments_to_message(
            sqlite_session,
            attachment_ids=[att.id],
            message_id=msg_id,
            chat_id=wrong_chat,
            uploader_sub=admin.sub,
        )


async def test_link_attachments_wrong_uploader(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    with patch("app.portal_chat.services.attachment.async_upload_file", new_callable=AsyncMock, return_value="sk"):
        att = await att_svc.upload_attachment(
            sqlite_session,
            file_data=io.BytesIO(b"1"),
            file_size=1,
            content_type="text/plain",
            original_filename="a.txt",
            uploader_sub=admin.sub,
            chat_id=chat.id,
        )
    with pytest.raises(ForbiddenError, match="другим пользователем"):
        await att_svc.link_attachments_to_message(
            sqlite_session,
            attachment_ids=[att.id],
            message_id=uuid.uuid4(),
            chat_id=chat.id,
            uploader_sub=other.sub,
        )


async def test_link_attachments_already_linked(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    m1 = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="a"))
    m2 = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="b"))
    with patch("app.portal_chat.services.attachment.async_upload_file", new_callable=AsyncMock, return_value="sk"):
        att = await att_svc.upload_attachment(
            sqlite_session,
            file_data=io.BytesIO(b"1"),
            file_size=1,
            content_type="text/plain",
            original_filename="a.txt",
            uploader_sub=admin.sub,
            chat_id=chat.id,
        )
    await att_svc.link_attachments_to_message(
        sqlite_session,
        attachment_ids=[att.id],
        message_id=m1.id,
        chat_id=chat.id,
        uploader_sub=admin.sub,
    )
    with pytest.raises(ForbiddenError, match="уже привязано"):
        await att_svc.link_attachments_to_message(
            sqlite_session,
            attachment_ids=[att.id],
            message_id=m2.id,
            chat_id=chat.id,
            uploader_sub=admin.sub,
        )


async def test_purge_orphan_invalid_hours(
    sqlite_session: AsyncSession,
) -> None:
    with pytest.raises(ValueError, match="положительным"):
        await att_svc.purge_orphan_attachments_older_than(sqlite_session, min_age_hours=0)


async def test_purge_orphan_removes_old_row(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    old_time = datetime.now(UTC) - timedelta(days=10)
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub=admin.sub,
        original_filename="old.bin",
        content_type="application/octet-stream",
        file_size=1,
        storage_key="orphan-key",
        message_id=None,
    )
    sqlite_session.add(att)
    await sqlite_session.flush()
    await sqlite_session.execute(
        update(PortalChatAttachment).where(PortalChatAttachment.id == att.id).values(created_at=old_time)
    )
    await sqlite_session.commit()
    await sqlite_session.refresh(att)

    with patch("app.portal_chat.services.attachment.async_delete_objects", new_callable=AsyncMock) as del_mock:
        n = await att_svc.purge_orphan_attachments_older_than(sqlite_session, min_age_hours=1)
    assert n == 1
    del_mock.assert_called_once_with(["orphan-key"])


async def test_purge_orphan_minio_error(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    old_time = datetime.now(UTC) - timedelta(days=10)
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub=admin.sub,
        original_filename="old.bin",
        content_type="application/octet-stream",
        file_size=1,
        storage_key="bad-key",
        message_id=None,
    )
    sqlite_session.add(att)
    await sqlite_session.flush()
    await sqlite_session.execute(
        update(PortalChatAttachment).where(PortalChatAttachment.id == att.id).values(created_at=old_time)
    )
    await sqlite_session.commit()

    with patch(
        "app.portal_chat.services.attachment.async_delete_objects",
        new_callable=AsyncMock,
        side_effect=S3Error(MagicMock(), "Err", "x", None, None, None),
    ):
        with pytest.raises(StorageUnavailableError):
            await att_svc.purge_orphan_attachments_older_than(sqlite_session, min_age_hours=1)


async def test_purge_attachments_linked_to_soft_deleted(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    with patch("app.portal_chat.services.attachment.async_upload_file", new_callable=AsyncMock, return_value="sk"):
        att_up = await att_svc.upload_attachment(
            sqlite_session,
            file_data=io.BytesIO(b"1"),
            file_size=1,
            content_type="text/plain",
            original_filename="z.bin",
            uploader_sub=admin.sub,
            chat_id=chat.id,
        )
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="текст", attachment_ids=[att_up.id]),
    )
    now = datetime.now(UTC)
    await sqlite_session.execute(
        update(PortalChatMessage).where(PortalChatMessage.id == msg.id).values(deleted_for_all_at=now, body="")
    )
    await sqlite_session.commit()

    with patch("app.portal_chat.services.attachment.async_delete_objects", new_callable=AsyncMock) as del_mock:
        n = await att_svc.purge_attachments_linked_to_soft_deleted_messages(sqlite_session)
    assert n == 1
    del_mock.assert_called_once_with([att_up.storage_key])


async def test_update_message_non_author_forbidden(
    sqlite_session: AsyncSession,
    mock_delete_object_ok: MagicMock,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="моё"),
    )
    msg.__dict__.pop("attachments", None)
    await sqlite_session.refresh(msg)
    with pytest.raises(ForbiddenError, match="чужое"):
        await update_message(
            sqlite_session,
            other,
            chat.id,
            msg.id,
            PortalChatMessageUpdate(body="взлом"),
        )


async def test_update_message_soft_deleted_forbidden(
    sqlite_session: AsyncSession,
    mock_delete_object_ok: MagicMock,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="x"),
    )
    msg.__dict__.pop("attachments", None)
    await sqlite_session.refresh(msg)
    mid = msg.id
    await delete_message_for_all(sqlite_session, admin, chat.id, mid)
    with pytest.raises(ForbiddenError, match="удалено"):
        await update_message(
            sqlite_session,
            admin,
            chat.id,
            mid,
            PortalChatMessageUpdate(body="y"),
        )


async def test_delete_message_for_all_non_author_forbidden(
    sqlite_session: AsyncSession,
    mock_delete_object_ok: MagicMock,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="автор админ"),
    )
    msg.__dict__.pop("attachments", None)
    await sqlite_session.refresh(msg)
    with pytest.raises(ForbiddenError, match="только автор"):
        await delete_message_for_all(sqlite_session, other, chat.id, msg.id)


async def test_create_chat_adds_member_subs(
    sqlite_session: AsyncSession,
    mock_delete_object_ok: MagicMock,
) -> None:
    admin = user_portal_admin()
    reg = user_portal_regular()
    ub = user_portal_user_b()
    chat = await create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Группа+", member_subs=[reg.sub, ub.sub]),
    )
    members = await chat_svc.list_chat_members(sqlite_session, chat.id)
    subs = {m.user_sub for m in members}
    assert subs == {admin.sub, reg.sub, ub.sub}


async def test_update_message_wrong_chat_id_not_found(
    sqlite_session: AsyncSession,
    mock_delete_object_ok: MagicMock,
) -> None:
    admin = user_portal_admin()
    chat_a = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    chat_b = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_user_b().sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat_a.id,
        PortalChatMessageCreate(body="только в A"),
    )
    mid = msg.id
    with pytest.raises(NotFoundError, match="не найдено"):
        await update_message(
            sqlite_session,
            admin,
            chat_b.id,
            mid,
            PortalChatMessageUpdate(body="x"),
        )


async def test_mark_chat_read_publishes(
    sqlite_session: AsyncSession,
    mock_delete_object_ok: MagicMock,
) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    mgr = MagicMock(publish=AsyncMock())
    with patch("app.portal_chat.services._mutations_chats.get_chat_manager", return_value=mgr):
        await chat_svc.mark_chat_read(sqlite_session, admin, chat.id)
    mgr.publish.assert_awaited_once()
    assert mgr.publish.await_args.args[1]["event"] == "read_state_updated"
