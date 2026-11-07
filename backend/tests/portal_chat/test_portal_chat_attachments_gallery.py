"""Тесты галереи вложений чата: GET /portal/chats/{id}/attachments.

Покрытие (testing.mdc): успешный сценарий + фильтр по типу + пагинация, исключение
вложений удалённых/скрытых для пользователя сообщений и «осиротевших» (без message_id)
вложений, 403 для не-участника чата.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.infrastructure.db.models.portal_chat import PortalChatAttachment
from app.main import app
from app.portal_chat.schemas.chat import PortalChatMessageCreate
from app.portal_chat.services import chat as chat_svc
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b


async def _attach(
    session: AsyncSession,
    *,
    chat_id: uuid.UUID,
    message_id: uuid.UUID | None,
    uploader_sub: str,
    content_type: str,
    filename: str = "f",
) -> PortalChatAttachment:
    att = PortalChatAttachment(
        chat_id=chat_id,
        message_id=message_id,
        uploader_sub=uploader_sub,
        original_filename=filename,
        content_type=content_type,
        file_size=1,
        storage_key=f"key-{uuid.uuid4()}",
    )
    session.add(att)
    await session.commit()
    await session.refresh(att)
    return att


async def test_list_chat_attachments_filters_by_kind(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="x"))

    img = await _attach(
        sqlite_session, chat_id=chat.id, message_id=msg.id, uploader_sub=admin.sub, content_type="image/png"
    )
    voice = await _attach(
        sqlite_session, chat_id=chat.id, message_id=msg.id, uploader_sub=admin.sub, content_type="audio/webm"
    )
    doc = await _attach(
        sqlite_session, chat_id=chat.id, message_id=msg.id, uploader_sub=admin.sub, content_type="application/pdf"
    )

    media, media_total = await chat_svc.list_chat_attachments(sqlite_session, admin, chat.id, kind="media")
    assert [a.id for a in media] == [img.id]
    assert media_total == 1

    audio, audio_total = await chat_svc.list_chat_attachments(sqlite_session, admin, chat.id, kind="audio")
    assert [a.id for a in audio] == [voice.id]
    assert audio_total == 1

    files, files_total = await chat_svc.list_chat_attachments(sqlite_session, admin, chat.id, kind="file")
    assert [a.id for a in files] == [doc.id]
    assert files_total == 1

    all_atts, all_total = await chat_svc.list_chat_attachments(sqlite_session, admin, chat.id, kind=None)
    assert all_total == 3
    assert {a.id for a in all_atts} == {img.id, voice.id, doc.id}


async def test_list_chat_attachments_pagination(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="x"))

    created = [
        await _attach(
            sqlite_session,
            chat_id=chat.id,
            message_id=msg.id,
            uploader_sub=admin.sub,
            content_type="image/png",
            filename=f"f{i}",
        )
        for i in range(5)
    ]
    # Явно разносим created_at, иначе при одинаковой точности timestamp порядок будет недетерминирован.
    base = datetime.now(UTC) - timedelta(minutes=10)
    for i, att in enumerate(created):
        await sqlite_session.execute(
            update(PortalChatAttachment)
            .where(PortalChatAttachment.id == att.id)
            .values(created_at=base + timedelta(minutes=i))
        )
    await sqlite_session.commit()

    page1, total1 = await chat_svc.list_chat_attachments(sqlite_session, admin, chat.id, kind="media", skip=0, limit=2)
    page2, total2 = await chat_svc.list_chat_attachments(sqlite_session, admin, chat.id, kind="media", skip=2, limit=2)

    assert total1 == total2 == 5
    assert len(page1) == 2
    assert len(page2) == 2
    # новые вложения — первыми (created.reverse())
    expected_order = [a.id for a in reversed(created)]
    assert [a.id for a in page1] == expected_order[:2]
    assert [a.id for a in page2] == expected_order[2:4]


async def test_list_chat_attachments_excludes_deleted_message(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="удалю"))
    msg.__dict__.pop("attachments", None)
    await sqlite_session.refresh(msg)
    await _attach(sqlite_session, chat_id=chat.id, message_id=msg.id, uploader_sub=admin.sub, content_type="image/png")

    with patch("app.portal_chat.services._mutations.async_delete_object", new_callable=AsyncMock):
        await chat_svc.delete_message_for_all(sqlite_session, admin, chat.id, msg.id)

    atts, total = await chat_svc.list_chat_attachments(sqlite_session, admin, chat.id)
    assert atts == []
    assert total == 0


async def test_list_chat_attachments_excludes_hidden_for_user(sqlite_session: AsyncSession) -> None:
    """Вложение сообщения, скрытого «у меня», не показывается этому пользователю, но видно другим."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="x"))
    msg.__dict__.pop("attachments", None)
    await sqlite_session.refresh(msg)
    await _attach(sqlite_session, chat_id=chat.id, message_id=msg.id, uploader_sub=admin.sub, content_type="image/png")

    await chat_svc.delete_message_for_user(sqlite_session, other, chat.id, msg.id)

    atts_other, total_other = await chat_svc.list_chat_attachments(sqlite_session, other, chat.id)
    assert atts_other == []
    assert total_other == 0

    atts_admin, total_admin = await chat_svc.list_chat_attachments(sqlite_session, admin, chat.id)
    assert total_admin == 1


async def test_list_chat_attachments_excludes_unlinked_orphan(sqlite_session: AsyncSession) -> None:
    """Вложения без message_id (не отправленные в составе сообщения) не входят в галерею."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    await _attach(sqlite_session, chat_id=chat.id, message_id=None, uploader_sub=admin.sub, content_type="image/png")

    atts, total = await chat_svc.list_chat_attachments(sqlite_session, admin, chat.id)
    assert atts == []
    assert total == 0


# ---------------------------------------------------------------------------
# HTTP-уровень: GET /portal/chats/{id}/attachments
# ---------------------------------------------------------------------------


async def test_list_chat_attachments_route_success(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
) -> None:
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Чат с галереей", "member_subs": [user_portal_regular().sub]},
    )
    chat_id = r_chat.json()["id"]
    r_msg = await client_admin.post(f"/api/v1/portal/chats/{chat_id}/messages", json={"body": "текст"})
    message_id = r_msg.json()["id"]
    await _attach(
        sqlite_session,
        chat_id=uuid.UUID(chat_id),
        message_id=uuid.UUID(message_id),
        uploader_sub=user_portal_admin().sub,
        content_type="image/png",
    )

    with patch("app.portal_chat.routes.messages.att_svc.build_download_url", return_value="https://dl.example/x"):
        r = await client_admin.get(f"/api/v1/portal/chats/{chat_id}/attachments", params={"kind": "media"})

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["message_id"] == message_id
    assert data["items"][0]["download_url"] == "https://dl.example/x"


async def test_list_chat_attachments_route_403_non_member(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_chat = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Закрытый", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r_chat.json()["id"]

    app.dependency_overrides[get_current_user] = user_portal_user_b
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get(f"/api/v1/portal/chats/{chat_id}/attachments")
    from tests.portal_chat.conftest import assert_api_error

    assert_api_error(r, 403, "forbidden")

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)
