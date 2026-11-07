"""Юнит-тесты сервиса чтения portal_chat (_queries)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from app.core.auth_constants import IDP_GROUP_PORTAL_ADMIN
from app.infrastructure.db.models.portal_chat import PortalChatAttachment
from app.portal_chat.schemas.chat import PortalChatMessageCreate
from app.portal_chat.services import chat as chat_svc
from app.schemas.auth import UserPublic
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b


async def test_search_messages_for_user_finds_substring_in_dm(
    sqlite_session: AsyncSession,
) -> None:
    """Поиск по телу сообщения в DM, где пользователь — участник."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="Уникальная строка для поиска alpha"),
    )
    rows = await chat_svc.search_messages_for_user(sqlite_session, admin, "alpha")
    assert len(rows) == 1
    msg, ch = rows[0]
    assert msg.body == "Уникальная строка для поиска alpha"
    assert ch.id == chat.id


async def test_search_messages_for_user_finds_substring_in_group_chat(
    sqlite_session: AsyncSession,
) -> None:
    """Поиск по телу сообщения в групповом чате (участник видит, посторонний — нет)."""
    from app.portal_chat.schemas.chat import PortalChatCreate

    author = user_portal_admin()
    member = user_portal_regular()
    outsider = user_portal_user_b()
    group = await chat_svc.create_chat(
        sqlite_session,
        author,
        PortalChatCreate(title="Команда Альфа", member_subs=[member.sub]),
    )
    await chat_svc.post_message(
        sqlite_session,
        author,
        group.id,
        PortalChatMessageCreate(body="обсуждаем групповой маркер beta-release"),
    )
    rows_member = await chat_svc.search_messages_for_user(sqlite_session, member, "beta-release")
    assert len(rows_member) == 1
    assert rows_member[0][1].id == group.id

    rows_author = await chat_svc.search_messages_for_user(sqlite_session, author, "beta-release")
    assert len(rows_author) == 1

    rows_outsider = await chat_svc.search_messages_for_user(sqlite_session, outsider, "beta-release")
    assert rows_outsider == []


async def test_search_messages_for_user_with_percent_in_query(
    sqlite_session: AsyncSession,
) -> None:
    """Поиск литерала % в теле (экранирование шаблона)."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="скидка 50% на всё"),
    )
    rows = await chat_svc.search_messages_for_user(sqlite_session, admin, "50%")
    assert len(rows) == 1


async def test_user_can_access_message_member_true(
    sqlite_session: AsyncSession,
) -> None:
    """Участник DM может обращаться к сообщению."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="x"),
    )
    ok = await chat_svc.user_can_access_message(sqlite_session, other, msg.id)
    assert ok is True


async def test_user_can_access_message_missing_false(
    sqlite_session: AsyncSession,
) -> None:
    """Несуществующее сообщение — False."""
    admin = user_portal_admin()
    ok = await chat_svc.user_can_access_message(sqlite_session, admin, uuid.uuid4())
    assert ok is False


async def test_user_can_access_message_stranger_false(
    sqlite_session: AsyncSession,
) -> None:
    """Пользователь вне чата — False."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="секрет"),
    )
    stranger = user_portal_user_b()
    ok = await chat_svc.user_can_access_message(sqlite_session, stranger, msg.id)
    assert ok is False


async def test_user_can_access_message_admin_without_membership_true(
    sqlite_session: AsyncSession,
) -> None:
    """Админ портала видит сообщение без членства в DM (политика _queries)."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, other, admin.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        other,
        chat.id,
        PortalChatMessageCreate(body="от другого"),
    )
    outsider_admin = UserPublic(
        sub="another-admin-sub",
        email="x@example.com",
        username="x",
        full_name="X",
        idp_groups=[IDP_GROUP_PORTAL_ADMIN],
        is_portal_admin=True,
    )
    ok = await chat_svc.user_can_access_message(sqlite_session, outsider_admin, msg.id)
    assert ok is True


async def test_message_to_read_presigned_url_failure_empty_string(
    sqlite_session: AsyncSession,
) -> None:
    """При ошибке presigned URL вложение получает пустой download_url."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="текст"),
    )
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub=admin.sub,
        original_filename="f.bin",
        content_type="application/octet-stream",
        file_size=1,
        storage_key="k1",
        message_id=msg.id,
    )
    sqlite_session.add(att)
    await sqlite_session.commit()
    await sqlite_session.refresh(att)
    msg.__dict__["attachments"] = [att]

    with patch(
        "app.infrastructure.storage.client.get_presigned_url",
        side_effect=RuntimeError("minio down"),
    ):
        read = chat_svc.message_to_read(msg)
    assert len(read.attachments) == 1
    assert read.attachments[0].download_url == ""


async def test_message_to_read_for_viewer_receipt_none_for_peer(
    sqlite_session: AsyncSession,
) -> None:
    """У собеседника receipt не показывается (только у автора)."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="hi"),
    )
    members = await chat_svc.list_chat_members(sqlite_session, chat.id)
    read_author = chat_svc.message_to_read_for_viewer(msg, admin.sub, members)
    read_peer = chat_svc.message_to_read_for_viewer(msg, other.sub, members)
    assert read_author.receipt in ("sent", "read")
    assert read_peer.receipt is None


async def test_list_chats_admin_not_member_group_not_visible(
    sqlite_session: AsyncSession,
) -> None:
    """portal_admin не видит групповой чат, в который его не добавили."""
    other = user_portal_regular()
    user_b = user_portal_user_b()
    from app.portal_chat.schemas.chat import PortalChatCreate

    group = await chat_svc.create_chat(
        sqlite_session,
        other,
        PortalChatCreate(title="Секретная группа", member_subs=[user_b.sub]),
    )

    admin = user_portal_admin()
    chats = await chat_svc.list_chats_for_user(sqlite_session, admin)
    assert all(c.id != group.id for c in chats), "admin не должен видеть чат без членства"


async def test_list_chats_admin_member_group_visible(
    sqlite_session: AsyncSession,
) -> None:
    """portal_admin видит групповой чат, в который его добавили."""
    admin = user_portal_admin()
    other = user_portal_regular()
    from app.portal_chat.schemas.chat import PortalChatCreate

    group = await chat_svc.create_chat(
        sqlite_session,
        other,
        PortalChatCreate(title="Открытая группа", member_subs=[admin.sub]),
    )

    chats = await chat_svc.list_chats_for_user(sqlite_session, admin)
    assert any(c.id == group.id for c in chats), "admin должен видеть чат, в котором участвует"


async def test_get_batch_unread_counts_empty_chat_ids(
    sqlite_session: AsyncSession,
) -> None:
    """Пустой список chat_ids — пустой словарь."""
    out = await chat_svc.get_batch_unread_counts(sqlite_session, "any-sub", [])
    assert out == {}


async def test_get_message_readers_returns_who_read(
    sqlite_session: AsyncSession,
) -> None:
    """Участник, у которого last_read_at >= created_at сообщения, попадает в readers."""
    author = user_portal_admin()
    reader = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, author, reader.sub)
    msg = await chat_svc.post_message(sqlite_session, author, chat.id, PortalChatMessageCreate(body="прочитай меня"))
    # Помечаем чат прочитанным от имени reader — выставляет last_read_at = now()
    await chat_svc.mark_chat_read(sqlite_session, reader, chat.id)

    readers = await chat_svc.get_message_readers(sqlite_session, author, chat.id, msg.id)
    reader_subs = [r.user_sub for r in readers]
    assert reader.sub in reader_subs
    assert author.sub not in reader_subs


async def test_get_message_readers_empty_when_none_read(
    sqlite_session: AsyncSession,
) -> None:
    """Если никто не читал чат после сообщения — список пуст."""
    author = user_portal_admin()
    reader = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, author, reader.sub)
    msg = await chat_svc.post_message(sqlite_session, author, chat.id, PortalChatMessageCreate(body="никто не читал"))

    readers = await chat_svc.get_message_readers(sqlite_session, author, chat.id, msg.id)
    assert readers == []


async def test_get_message_readers_forbidden_for_non_member(
    sqlite_session: AsyncSession,
) -> None:
    """Не-участник чата получает ForbiddenError при запросе readers."""
    from app.core.exceptions import ForbiddenError

    author = user_portal_admin()
    member = user_portal_regular()
    outsider = user_portal_user_b()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, author, member.sub)
    msg = await chat_svc.post_message(sqlite_session, author, chat.id, PortalChatMessageCreate(body="секрет"))

    import pytest

    with pytest.raises(ForbiddenError):
        await chat_svc.get_message_readers(sqlite_session, outsider, chat.id, msg.id)


async def test_get_message_reaction_reactors_returns_who_reacted(
    sqlite_session: AsyncSession,
) -> None:
    """Пользователи, поставившие эмодзи, попадают в reactors в порядке created_at."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.infrastructure.db.models.portal_chat import PortalChatMessage
    from app.portal_chat.services._mutations_reactions import toggle_message_reaction

    author = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, author, other.sub)
    msg = await chat_svc.post_message(sqlite_session, author, chat.id, PortalChatMessageCreate(body="реакции"))

    async def _toggle(user: object, emoji: str) -> None:
        row = await sqlite_session.get(PortalChatMessage, msg.id)
        assert row is not None
        row.__dict__.pop("attachments", None)
        await toggle_message_reaction(sqlite_session, user, chat.id, msg.id, emoji)

    mgr = MagicMock(publish=AsyncMock())
    with patch("app.infrastructure.ws.managers.get_chat_manager", return_value=mgr):
        await _toggle(author, "👍")
        await _toggle(other, "👍")

    reactors = await chat_svc.get_message_reaction_reactors(sqlite_session, author, chat.id, msg.id, "👍")
    assert [r.user_sub for r in reactors] == [author.sub, other.sub]


async def test_get_message_reaction_reactors_empty_for_other_emoji(
    sqlite_session: AsyncSession,
) -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.infrastructure.db.models.portal_chat import PortalChatMessage
    from app.portal_chat.services._mutations_reactions import toggle_message_reaction

    author = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, author, other.sub)
    msg = await chat_svc.post_message(sqlite_session, author, chat.id, PortalChatMessageCreate(body="ок"))
    row = await sqlite_session.get(PortalChatMessage, msg.id)
    assert row is not None
    row.__dict__.pop("attachments", None)
    mgr = MagicMock(publish=AsyncMock())
    with patch("app.infrastructure.ws.managers.get_chat_manager", return_value=mgr):
        await toggle_message_reaction(sqlite_session, author, chat.id, msg.id, "👍")

    reactors = await chat_svc.get_message_reaction_reactors(sqlite_session, author, chat.id, msg.id, "❤️")
    assert reactors == []


async def test_get_message_reaction_reactors_forbidden_for_non_member(
    sqlite_session: AsyncSession,
) -> None:
    from unittest.mock import AsyncMock, MagicMock, patch

    from app.core.exceptions import ForbiddenError
    from app.infrastructure.db.models.portal_chat import PortalChatMessage
    from app.portal_chat.services._mutations_reactions import toggle_message_reaction

    author = user_portal_admin()
    member = user_portal_regular()
    outsider = user_portal_user_b()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, author, member.sub)
    msg = await chat_svc.post_message(sqlite_session, author, chat.id, PortalChatMessageCreate(body="секрет"))
    row = await sqlite_session.get(PortalChatMessage, msg.id)
    assert row is not None
    row.__dict__.pop("attachments", None)
    mgr = MagicMock(publish=AsyncMock())
    with patch("app.infrastructure.ws.managers.get_chat_manager", return_value=mgr):
        await toggle_message_reaction(sqlite_session, author, chat.id, msg.id, "🔥")

    import pytest

    with pytest.raises(ForbiddenError):
        await chat_svc.get_message_reaction_reactors(sqlite_session, outsider, chat.id, msg.id, "🔥")


async def test_post_message_with_reply_quote_text(
    sqlite_session: AsyncSession,
) -> None:
    """Ответ с цитатой сохраняет reply_quote_text и отдаёт его в reply_to.quote_text."""
    author = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, author, other.sub)
    original = await chat_svc.post_message(
        sqlite_session,
        author,
        chat.id,
        PortalChatMessageCreate(body="привет мир, как дела"),
    )
    reply = await chat_svc.post_message(
        sqlite_session,
        other,
        chat.id,
        PortalChatMessageCreate(
            body="ок",
            reply_to_message_id=original.id,
            reply_quote_text="привет мир",
        ),
    )
    assert reply.reply_quote_text == "привет мир"
    read = chat_svc.message_to_read(reply)
    assert read.reply_to is not None
    assert read.reply_to.quote_text == "привет мир"
    assert read.reply_to.body == "привет мир"


async def test_post_message_reply_quote_must_be_substring(
    sqlite_session: AsyncSession,
) -> None:
    import pytest
    from app.core.exceptions import ValidationError

    author = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, author, other.sub)
    original = await chat_svc.post_message(
        sqlite_session,
        author,
        chat.id,
        PortalChatMessageCreate(body="только это"),
    )
    with pytest.raises(ValidationError):
        await chat_svc.post_message(
            sqlite_session,
            other,
            chat.id,
            PortalChatMessageCreate(
                body="нет",
                reply_to_message_id=original.id,
                reply_quote_text="чужой текст",
            ),
        )


async def test_post_message_reply_quote_empty_after_strip_becomes_none(
    sqlite_session: AsyncSession,
) -> None:
    author = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, author, other.sub)
    original = await chat_svc.post_message(
        sqlite_session,
        author,
        chat.id,
        PortalChatMessageCreate(body="текст"),
    )
    reply = await chat_svc.post_message(
        sqlite_session,
        other,
        chat.id,
        PortalChatMessageCreate(
            body="ок",
            reply_to_message_id=original.id,
            reply_quote_text="   ",
        ),
    )
    assert reply.reply_quote_text is None


async def test_post_message_reply_quote_without_reply_to_rejected() -> None:
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PortalChatMessageCreate(body="ок", reply_quote_text="цитата")


async def test_post_message_reply_quote_max_length_rejected() -> None:
    import pytest
    from app.portal_chat.constants import CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        PortalChatMessageCreate(
            body="ок",
            reply_to_message_id="00000000-0000-4000-8000-000000000001",
            reply_quote_text="x" * (CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH + 1),
        )


async def test_list_messages_loads_attachments_batch(
    sqlite_session: AsyncSession,
) -> None:
    """list_messages подгружает вложения в msg.__dict__."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="с вложением"),
    )
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub=admin.sub,
        original_filename="a.png",
        content_type="image/png",
        file_size=10,
        storage_key="sk",
        message_id=msg.id,
    )
    sqlite_session.add(att)
    await sqlite_session.commit()

    msgs = await chat_svc.list_messages(sqlite_session, admin, chat.id)
    assert len(msgs) == 1
    loaded = msgs[0].__dict__.get("attachments")
    assert loaded is not None
    assert len(loaded) == 1
    assert loaded[0].original_filename == "a.png"
