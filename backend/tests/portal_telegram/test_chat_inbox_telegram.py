from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.core.config import Settings
from app.infrastructure.db.models.portal_chat import (
    PortalChat,
    PortalChatAttachment,
    PortalChatMember,
    PortalChatMessage,
    PortalChatMessageHidden,
)
from app.portal_telegram.services.chat_inbox_telegram import (
    format_chat_inbox_telegram,
    source_message_visible_for_recipient,
)


@pytest.mark.asyncio
async def test_format_dm_uses_peer_profile_name(sqlite_session) -> None:
    cid = uuid.uuid4()
    sqlite_session.add(
        PortalChat(
            id=cid,
            title=None,
            created_by_sub="user-sub",
            canonical_dm_key="pair:user-sub:admin-sub",
        )
    )
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="user-sub"))
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="admin-sub"))
    await sqlite_session.commit()

    s = Settings(database_url="sqlite+aiosqlite:///:memory:", portal_public_url="https://portal.example")
    result = await format_chat_inbox_telegram(
        sqlite_session,
        recipient_sub="user-sub",
        chat_id=cid,
        kind="dm",
        settings=s,
    )
    assert result is not None
    text, url = result
    assert text.splitlines()[0] == "💬 Сообщение!"
    assert "Обновление в чатах на портале" not in text
    assert "Admin" in text
    assert "/chats?chat=" in url


@pytest.mark.asyncio
async def test_format_dm_includes_last_message_preview(sqlite_session) -> None:
    cid = uuid.uuid4()
    sqlite_session.add(
        PortalChat(
            id=cid,
            title=None,
            created_by_sub="user-sub",
            canonical_dm_key="pair:user-sub:admin-sub",
        )
    )
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="user-sub"))
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="admin-sub"))
    sqlite_session.add(
        PortalChatMessage(
            chat_id=cid,
            author_sub="admin-sub",
            body="Последнее сообщение для превью TG",
        )
    )
    await sqlite_session.commit()

    s = Settings(database_url="sqlite+aiosqlite:///:memory:", portal_public_url="https://portal.example")
    result = await format_chat_inbox_telegram(
        sqlite_session,
        recipient_sub="user-sub",
        chat_id=cid,
        kind="dm",
        settings=s,
    )
    assert result is not None
    text, _url = result
    assert "От:" not in text
    assert "Последнее сообщение для превью TG" in text


@pytest.mark.asyncio
async def test_format_not_member_returns_none(sqlite_session) -> None:
    cid = uuid.uuid4()
    sqlite_session.add(
        PortalChat(
            id=cid,
            title="Группа",
            created_by_sub="admin-sub",
            canonical_dm_key=None,
        )
    )
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="admin-sub"))
    await sqlite_session.commit()

    s = Settings(database_url="sqlite+aiosqlite:///:memory:", portal_public_url="https://portal.example")
    result = await format_chat_inbox_telegram(
        sqlite_session,
        recipient_sub="user-sub",
        chat_id=cid,
        kind="group",
        settings=s,
    )
    assert result is None


@pytest.mark.asyncio
async def test_format_chat_not_found_returns_none(sqlite_session) -> None:
    missing_id = uuid.uuid4()
    s = Settings(database_url="sqlite+aiosqlite:///:memory:", portal_public_url="https://portal.example")
    result = await format_chat_inbox_telegram(
        sqlite_session,
        recipient_sub="user-sub",
        chat_id=missing_id,
        kind="dm",
        settings=s,
    )
    assert result is None


@pytest.mark.asyncio
async def test_format_group_includes_sender_line(sqlite_session) -> None:
    cid = uuid.uuid4()
    sqlite_session.add(
        PortalChat(
            id=cid,
            title="Группа для TG",
            created_by_sub="admin-sub",
            canonical_dm_key=None,
        )
    )
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="user-sub"))
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="admin-sub"))
    sqlite_session.add(
        PortalChatMessage(
            chat_id=cid,
            author_sub="admin-sub",
            body="Сообщение от админа в группе",
        )
    )
    await sqlite_session.commit()

    s = Settings(database_url="sqlite+aiosqlite:///:memory:", portal_public_url="https://portal.example")
    result = await format_chat_inbox_telegram(
        sqlite_session,
        recipient_sub="user-sub",
        chat_id=cid,
        kind="group",
        settings=s,
    )
    assert result is not None
    text, _url = result
    assert text.splitlines()[0] == "👥 Сообщение!"
    assert "Обновление в чатах на портале" not in text
    assert "От: Admin" in text
    assert "Сообщение от админа в группе" in text


@pytest.mark.asyncio
async def test_format_uses_explicit_chat_title(sqlite_session) -> None:
    cid = uuid.uuid4()
    sqlite_session.add(
        PortalChat(
            id=cid,
            title="  Явный заголовок  ",
            created_by_sub="admin-sub",
            canonical_dm_key=None,
        )
    )
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="user-sub"))
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="admin-sub"))
    await sqlite_session.commit()

    s = Settings(database_url="sqlite+aiosqlite:///:memory:", portal_public_url="https://portal.example")
    result = await format_chat_inbox_telegram(
        sqlite_session,
        recipient_sub="user-sub",
        chat_id=cid,
        kind="group",
        settings=s,
    )
    assert result is not None
    text, _url = result
    assert "Явный заголовок" in text
    assert "групповом чате" in text


@pytest.mark.asyncio
async def test_format_shows_attachment_label_when_body_empty(sqlite_session) -> None:
    cid = uuid.uuid4()
    sqlite_session.add(
        PortalChat(
            id=cid,
            title="Чат вложений",
            created_by_sub="admin-sub",
            canonical_dm_key=None,
        )
    )
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="user-sub"))
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="admin-sub"))
    mid = uuid.uuid4()
    sqlite_session.add(
        PortalChatMessage(
            id=mid,
            chat_id=cid,
            author_sub="admin-sub",
            body="",
        )
    )
    await sqlite_session.flush()
    sqlite_session.add(
        PortalChatAttachment(
            message_id=mid,
            chat_id=cid,
            uploader_sub="admin-sub",
            original_filename="f.pdf",
            content_type="application/pdf",
            file_size=10,
            storage_key=f"unique-key-{mid}",
        )
    )
    await sqlite_session.commit()

    s = Settings(database_url="sqlite+aiosqlite:///:memory:", portal_public_url="https://portal.example")
    result = await format_chat_inbox_telegram(
        sqlite_session,
        recipient_sub="user-sub",
        chat_id=cid,
        kind="dm",
        settings=s,
    )
    assert result is not None
    text, _url = result
    assert "Вложение" in text


@pytest.mark.asyncio
async def test_source_message_deleted_or_hidden_is_not_visible(sqlite_session) -> None:
    cid = uuid.uuid4()
    deleted_id = uuid.uuid4()
    hidden_id = uuid.uuid4()
    now = datetime.now(UTC)
    sqlite_session.add(PortalChat(id=cid, title="Чат", created_by_sub="admin-sub"))
    sqlite_session.add(PortalChatMember(chat_id=cid, user_sub="user-sub"))
    sqlite_session.add(
        PortalChatMessage(
            id=deleted_id,
            chat_id=cid,
            author_sub="admin-sub",
            body="удалено",
            deleted_for_all_at=now,
        )
    )
    sqlite_session.add(
        PortalChatMessage(
            id=hidden_id,
            chat_id=cid,
            author_sub="admin-sub",
            body="скрыто",
        )
    )
    sqlite_session.add(
        PortalChatMessageHidden(user_sub="user-sub", message_id=hidden_id, chat_id=cid),
    )
    await sqlite_session.commit()

    assert (
        await source_message_visible_for_recipient(
            sqlite_session,
            chat_id=cid,
            message_id=deleted_id,
            recipient_sub="user-sub",
        )
        is False
    )
    assert (
        await source_message_visible_for_recipient(
            sqlite_session,
            chat_id=cid,
            message_id=hidden_id,
            recipient_sub="user-sub",
        )
        is False
    )
    assert (
        await source_message_visible_for_recipient(
            sqlite_session,
            chat_id=cid,
            message_id=hidden_id,
            recipient_sub="admin-sub",
        )
        is True
    )
