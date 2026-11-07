"""Сценарии аудита portal_chat: admin read-only, hidden, presign, edit, waveform, DELETE."""

from __future__ import annotations

import io
import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.infrastructure.db.models.portal_chat import PortalChatAttachment
from app.portal_chat.constants import VOICE_WAVEFORM_BARS
from app.portal_chat.schemas.chat import PortalChatCreate, PortalChatMessageCreate, PortalChatMessageUpdate
from app.portal_chat.services import _mutations_pin as pin_svc
from app.portal_chat.services import attachment as att_svc
from app.portal_chat.services import chat as chat_svc
from app.portal_chat.services import group_chat as group_svc
from app.portal_chat.services._mutations_reactions import toggle_message_reaction
from app.portal_chat.services.attachment import parse_voice_waveform_json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b
from tests.portal_chat.conftest import assert_api_error


async def _fresh(session: AsyncSession, msg: object) -> None:
    msg.__dict__.pop("attachments", None)  # type: ignore[union-attr]
    await session.refresh(msg)  # type: ignore[arg-type]


async def _http_as(session: AsyncSession, user_factory: object) -> AsyncIterator[AsyncClient]:
    from tests.portal_chat.conftest import async_client_as

    async with async_client_as(session, user_factory) as ac:  # type: ignore[arg-type]
        yield ac


# ─── Presign в ленте ───────────────────────────────────────────────────────────


async def test_message_to_read_presign_force_download_for_document(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="файл"))
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub=admin.sub,
        original_filename="doc.pdf",
        content_type="application/pdf",
        file_size=10,
        storage_key="pdf-key",
        message_id=msg.id,
    )
    sqlite_session.add(att)
    await sqlite_session.commit()
    msg.__dict__["attachments"] = [att]

    with patch(
        "app.infrastructure.storage.client.get_presigned_url",
        return_value="https://minio/pdf",
    ) as presign:
        read = chat_svc.message_to_read(msg)

    presign.assert_called_once()
    assert presign.call_args.kwargs["force_download"] is True
    assert read.attachments[0].download_url == "https://minio/pdf"


async def test_message_to_read_presign_inline_for_image(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="фото"))
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub=admin.sub,
        original_filename="a.png",
        content_type="image/png",
        file_size=10,
        storage_key="img-key",
        message_id=msg.id,
    )
    sqlite_session.add(att)
    await sqlite_session.commit()
    msg.__dict__["attachments"] = [att]

    with patch(
        "app.infrastructure.storage.client.get_presigned_url",
        return_value="https://minio/img",
    ) as presign:
        chat_svc.message_to_read(msg)

    assert presign.call_args.kwargs["force_download"] is False


# ─── Admin без членства: чтение да, запись нет ────────────────────────────────


async def test_admin_without_membership_reads_ok_writes_forbidden(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    regular = user_portal_regular()
    peer = user_portal_user_b()
    group = await chat_svc.create_chat(
        sqlite_session,
        regular,
        PortalChatCreate(title="Чужой чат", member_subs=[peer.sub]),
    )
    msg = await chat_svc.post_message(
        sqlite_session,
        regular,
        group.id,
        PortalChatMessageCreate(body="видно админу"),
    )
    att = PortalChatAttachment(
        chat_id=group.id,
        uploader_sub=regular.sub,
        original_filename="f.bin",
        content_type="application/octet-stream",
        file_size=4,
        storage_key="admin-read-key",
        message_id=msg.id,
    )
    sqlite_session.add(att)
    await sqlite_session.commit()

    async for ac in _http_as(sqlite_session, user_portal_admin):
        r_list = await ac.get(f"/api/v1/portal/chats/{group.id}/messages")
        assert r_list.status_code == 200, r_list.text
        assert any(m["id"] == str(msg.id) for m in r_list.json())

        r_pinned = await ac.get(f"/api/v1/portal/chats/{group.id}/messages/pinned")
        assert r_pinned.status_code == 200

        with patch(
            "app.portal_chat.services.attachment.get_presigned_url",
            return_value="https://dl.example/x",
        ):
            r_dl = await ac.get(f"/api/v1/portal/chats/{group.id}/attachments/{att.id}/download")
        assert r_dl.status_code == 200, r_dl.text

        r_post = await ac.post(
            f"/api/v1/portal/chats/{group.id}/messages",
            json={"body": "админ пишет"},
        )
        assert r_post.status_code == 403

        r_pin = await ac.post(f"/api/v1/portal/chats/{group.id}/messages/{msg.id}/pin")
        assert r_pin.status_code == 403

        r_react = await ac.post(
            f"/api/v1/portal/chats/{group.id}/messages/{msg.id}/reactions",
            json={"emoji": "👍"},
        )
        assert r_react.status_code == 403

        r_upload = await ac.post(
            f"/api/v1/portal/chats/{group.id}/attachments",
            files={"file": ("x.bin", io.BytesIO(b"1234"), "application/octet-stream")},
        )
        assert r_upload.status_code == 403

        r_tr = await ac.post(f"/api/v1/portal/chats/{group.id}/attachments/{att.id}/transcribe")
        assert r_tr.status_code == 403

        r_del = await ac.delete(f"/api/v1/portal/chats/{group.id}")
        assert_api_error(r_del, 404, "not_found")


# ─── Скрытие «удалить у меня» ─────────────────────────────────────────────────


async def test_hidden_message_secondary_apis_404(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    msg = await chat_svc.post_message(sqlite_session, admin, chat.id, PortalChatMessageCreate(body="секрет"))
    await _fresh(sqlite_session, msg)
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub=admin.sub,
        original_filename="h.bin",
        content_type="application/octet-stream",
        file_size=1,
        storage_key="hidden-key",
        message_id=msg.id,
    )
    sqlite_session.add(att)
    await sqlite_session.commit()

    mgr = MagicMock(publish=AsyncMock())
    with patch("app.infrastructure.ws.managers.get_chat_manager", return_value=mgr):
        await pin_svc.pin_message(sqlite_session, other, chat.id, msg.id)

    await chat_svc.delete_message_for_user(sqlite_session, other, chat.id, msg.id)

    with pytest.raises(NotFoundError):
        await pin_svc.pin_message(sqlite_session, other, chat.id, msg.id)
    with pytest.raises(NotFoundError):
        await pin_svc.unpin_message(sqlite_session, other, chat.id, msg.id)
    with pytest.raises(NotFoundError):
        await toggle_message_reaction(sqlite_session, other, chat.id, msg.id, "👍")
    with pytest.raises(NotFoundError):
        await chat_svc.get_message_readers(sqlite_session, other, chat.id, msg.id)
    with pytest.raises(NotFoundError):
        await att_svc.get_attachment_with_access_check(sqlite_session, att.id, other.sub, chat.id)

    pinned = await pin_svc.list_pinned_messages(sqlite_session, other, chat.id)
    assert pinned == []

    pinned_author = await pin_svc.list_pinned_messages(sqlite_session, admin, chat.id)
    assert [m.id for m in pinned_author] == [msg.id]


async def test_hidden_reply_preview_hides_body(sqlite_session: AsyncSession) -> None:
    author = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, author, other.sub)
    original = await chat_svc.post_message(
        sqlite_session,
        author,
        chat.id,
        PortalChatMessageCreate(body="секретное тело для цитаты"),
    )
    await chat_svc.post_message(
        sqlite_session,
        other,
        chat.id,
        PortalChatMessageCreate(body="ответ", reply_to_message_id=original.id),
    )
    await chat_svc.delete_message_for_user(sqlite_session, other, chat.id, original.id)

    msgs = await chat_svc.list_messages(sqlite_session, other, chat.id)
    assert len(msgs) == 1
    read = chat_svc.message_to_read(msgs[0])
    assert read.reply_to is not None
    assert read.reply_to.body == ""
    assert read.reply_to.quote_text is None


# ─── Редактирование сохраняет вложения ────────────────────────────────────────


async def test_update_message_keeps_attachments(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    with patch("app.portal_chat.services.attachment.async_upload_file", new_callable=AsyncMock, return_value="sk"):
        att = await att_svc.upload_attachment(
            sqlite_session,
            file_data=io.BytesIO(b"%PDF-1.4"),
            file_size=8,
            content_type="application/pdf",
            original_filename="keep.pdf",
            uploader_sub=admin.sub,
            chat_id=chat.id,
        )
    msg = await chat_svc.post_message(
        sqlite_session,
        admin,
        chat.id,
        PortalChatMessageCreate(body="до правки", attachment_ids=[att.id]),
    )
    await _fresh(sqlite_session, msg)

    mgr = MagicMock(publish=AsyncMock())
    with (
        patch("app.portal_chat.services._mutations.get_chat_manager", return_value=mgr),
        patch("app.infrastructure.storage.client.get_presigned_url", return_value="https://dl/keep"),
    ):
        updated = await chat_svc.update_message(
            sqlite_session,
            admin,
            chat.id,
            msg.id,
            PortalChatMessageUpdate(body="после правки"),
        )
        loaded = updated.__dict__.get("attachments")
        assert loaded is not None
        assert len(loaded) == 1
        assert loaded[0].original_filename == "keep.pdf"
        read = chat_svc.message_to_read(updated)
        assert len(read.attachments) == 1
        ws_payload = mgr.publish.await_args[0][1]
        assert ws_payload["event"] == "message_updated"
        assert len(ws_payload["message"]["attachments"]) == 1


# ─── Waveform ─────────────────────────────────────────────────────────────────


def test_parse_voice_waveform_accepts_28_values() -> None:
    bars = [i / 27 for i in range(VOICE_WAVEFORM_BARS)]
    parsed = parse_voice_waveform_json(json.dumps(bars))
    assert parsed is not None
    assert len(parsed) == VOICE_WAVEFORM_BARS
    assert parsed[0] == 0.0
    assert parsed[-1] == 1.0


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "[",
        "[1, 2]",
        json.dumps([2.0] * VOICE_WAVEFORM_BARS),
        json.dumps([0.1] * 5000),
    ],
)
def test_parse_voice_waveform_ignores_invalid(raw: str | None) -> None:
    assert parse_voice_waveform_json(raw) is None


# ─── HTTP DELETE /chats ───────────────────────────────────────────────────────


async def test_delete_chat_http_dm_member_204(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    admin = user_portal_admin()
    peer = user_portal_user_b()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, peer.sub)

    with (
        patch("app.portal_chat.services.delete_chat.async_delete_objects", new_callable=AsyncMock),
        patch(
            "app.portal_chat.services.delete_chat.get_chat_manager",
            return_value=MagicMock(publish=AsyncMock(), disconnect_user=AsyncMock()),
        ),
        patch("app.portal_chat.services.delete_chat.publish_chat_list_refresh", new_callable=AsyncMock),
        patch("app.portal_chat.services.delete_chat.delete_embeddings_batch", new_callable=AsyncMock),
    ):
        async for ac in _http_as(sqlite_session, user_portal_admin):
            r = await ac.delete(f"/api/v1/portal/chats/{chat.id}")
    assert r.status_code == 204


async def test_delete_chat_http_outsider_forbidden(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    admin = user_portal_admin()
    peer = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, peer.sub)

    async for ac in _http_as(sqlite_session, user_portal_user_b):
        r = await ac.delete(f"/api/v1/portal/chats/{chat.id}")
    from tests.portal_chat.conftest import assert_api_error

    assert_api_error(r, 404, "not_found")


# ─── Kick отключает WS ────────────────────────────────────────────────────────


async def test_remove_member_disconnects_user_from_ws(sqlite_session: AsyncSession) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Кик", member_subs=[regular.sub]),
    )
    mgr = MagicMock(publish=AsyncMock(), disconnect_user=AsyncMock())
    with (
        patch("app.portal_chat.services.group_chat.get_chat_manager", return_value=mgr),
        patch("app.infrastructure.ws.managers.get_chat_manager", return_value=mgr),
        patch("app.portal_chat.services.group_chat.publish_chat_list_refresh", new_callable=AsyncMock),
    ):
        await group_svc.remove_member_from_group_chat(sqlite_session, admin, chat.id, target_sub=regular.sub)

    mgr.disconnect_user.assert_awaited_once_with(chat.id, regular.sub)
