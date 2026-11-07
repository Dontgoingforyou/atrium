"""Тесты аватара группового чата (MinIO и WS мокаются)."""

from __future__ import annotations

import logging
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.core.exceptions import AppError, ForbiddenError
from app.portal_chat.schemas.chat import PortalChatCreate
from app.portal_chat.services import chat as chat_svc
from app.portal_chat.services import chat_avatar as chat_av
from fastapi import UploadFile
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular
from tests.portal_chat.conftest import CHAT_API, as_user, assert_api_error


def _upload_jpeg(data: bytes = b"\xff\xd8\xff\xe0", *, filename: str = "a.jpg") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(data),
        headers={"content-type": "image/jpeg"},
    )


@pytest.fixture
def _mock_chat_ws() -> object:
    mgr = MagicMock(publish=AsyncMock())
    with patch("app.portal_chat.services.chat_avatar.get_chat_manager", return_value=mgr):
        yield


@pytest.mark.asyncio
async def test_save_group_avatar_non_creator_forbidden(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Группа", member_subs=[regular.sub]),
    )
    with pytest.raises(ForbiddenError, match="создатель"):
        await chat_av.save_group_chat_avatar(
            sqlite_session,
            regular,
            chat.id,
            file=_upload_jpeg(),
        )


@pytest.mark.asyncio
async def test_save_group_avatar_dm_forbidden(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
) -> None:
    admin = user_portal_admin()
    dm = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, user_portal_regular().sub)
    with pytest.raises(ForbiddenError, match="группового"):
        await chat_av.save_group_chat_avatar(sqlite_session, admin, dm.id, file=_upload_jpeg())


@pytest.mark.asyncio
async def test_save_group_avatar_success(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Команда", member_subs=[user_portal_regular().sub]),
    )
    with (
        patch("app.portal_chat.services.chat_avatar.async_upload_bytes_to_key", new_callable=AsyncMock),
        patch(
            "app.portal_chat.services.chat_avatar.async_presign_avatar_url",
            new_callable=AsyncMock,
            return_value="https://signed.example/g",
        ),
        patch("app.portal_chat.services.chat_avatar.async_delete_object", new_callable=AsyncMock),
    ):
        out = await chat_av.save_group_chat_avatar(sqlite_session, admin, chat.id, file=_upload_jpeg())

    assert out["avatar_url"] == "https://signed.example/g"
    await sqlite_session.refresh(chat)
    assert chat.avatar_storage_key is not None
    assert "avatars/chats/" in chat.avatar_storage_key


@pytest.mark.asyncio
async def test_save_group_avatar_too_large(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
) -> None:
    from app.services.avatar_upload_common import AVATAR_MAX_BYTES

    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Большой", member_subs=[user_portal_regular().sub]),
    )
    big = b"x" * (AVATAR_MAX_BYTES + 1)
    with pytest.raises(AppError) as ei:
        await chat_av.save_group_chat_avatar(sqlite_session, admin, chat.id, file=_upload_jpeg(big))
    assert ei.value.status_code == 413


@pytest.mark.asyncio
async def test_clear_group_avatar_removes_storage(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="С ключом", member_subs=[user_portal_regular().sub]),
    )
    chat.avatar_storage_key = "avatars/chats/test/key.jpg"
    await sqlite_session.commit()

    with patch("app.portal_chat.services.chat_avatar.async_delete_object", new_callable=AsyncMock) as dm:
        await chat_av.clear_group_chat_avatar(sqlite_session, admin, chat.id)

    dm.assert_called_once_with("avatars/chats/test/key.jpg")
    await sqlite_session.refresh(chat)
    assert chat.avatar_storage_key is None


@pytest.mark.asyncio
async def test_save_group_avatar_sets_focal_coordinates(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Фокус", member_subs=[user_portal_regular().sub]),
    )
    with (
        patch("app.portal_chat.services.chat_avatar.async_upload_bytes_to_key", new_callable=AsyncMock),
        patch(
            "app.portal_chat.services.chat_avatar.async_presign_avatar_url",
            new_callable=AsyncMock,
            return_value="https://x",
        ),
        patch("app.portal_chat.services.chat_avatar.async_delete_object", new_callable=AsyncMock),
    ):
        out = await chat_av.save_group_chat_avatar(
            sqlite_session,
            admin,
            chat.id,
            file=_upload_jpeg(),
            avatar_focal_x=0.25,
            avatar_focal_y=0.75,
        )

    assert out["avatar_focal_x"] == pytest.approx(0.25)
    assert out["avatar_focal_y"] == pytest.approx(0.75)
    await sqlite_session.refresh(chat)
    assert chat.avatar_focal_x == pytest.approx(0.25)
    assert chat.avatar_focal_y == pytest.approx(0.75)


@pytest.mark.asyncio
async def test_save_group_avatar_deletes_previous_storage_key(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Замена", member_subs=[user_portal_regular().sub]),
    )
    chat.avatar_storage_key = "avatars/chats/prev/old.jpg"
    await sqlite_session.commit()
    await sqlite_session.refresh(chat)

    with (
        patch("app.portal_chat.services.chat_avatar.async_upload_bytes_to_key", new_callable=AsyncMock),
        patch(
            "app.portal_chat.services.chat_avatar.async_presign_avatar_url",
            new_callable=AsyncMock,
            return_value="https://x",
        ),
        patch("app.portal_chat.services.chat_avatar.async_delete_object", new_callable=AsyncMock) as dm,
    ):
        await chat_av.save_group_chat_avatar(sqlite_session, admin, chat.id, file=_upload_jpeg())

    await sqlite_session.refresh(chat)
    assert chat.avatar_storage_key != "avatars/chats/prev/old.jpg"
    dm.assert_any_call("avatars/chats/prev/old.jpg")


@pytest.mark.asyncio
async def test_save_group_avatar_upload_failure_rolls_back_and_deletes_partial_key(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Сбой MinIO", member_subs=[user_portal_regular().sub]),
    )

    def _fail_upload(**_: object) -> None:
        raise RuntimeError("minio down")

    deleted_keys: list[str] = []

    def _track_delete(key: str) -> None:
        deleted_keys.append(key)

    with (
        patch(
            "app.portal_chat.services.chat_avatar.async_upload_bytes_to_key",
            new_callable=AsyncMock,
            side_effect=_fail_upload,
        ),
        patch(
            "app.portal_chat.services.chat_avatar.async_delete_object",
            new_callable=AsyncMock,
            side_effect=_track_delete,
        ),
    ):
        with pytest.raises(RuntimeError, match="minio down"):
            await chat_av.save_group_chat_avatar(sqlite_session, admin, chat.id, file=_upload_jpeg())

    assert len(deleted_keys) == 1
    assert deleted_keys[0].startswith("avatars/chats/")
    await sqlite_session.refresh(chat)
    assert chat.avatar_storage_key is None


@pytest.mark.asyncio
async def test_clear_group_avatar_non_creator_forbidden(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
) -> None:
    admin = user_portal_admin()
    regular = user_portal_regular()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Доступ", member_subs=[regular.sub]),
    )
    with pytest.raises(ForbiddenError, match="создатель"):
        await chat_av.clear_group_chat_avatar(sqlite_session, regular, chat.id)


@pytest.mark.asyncio
async def test_clear_group_avatar_noop_when_no_storage_key(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Пусто", member_subs=[user_portal_regular().sub]),
    )
    mgr = MagicMock(publish=AsyncMock())
    with (
        patch("app.portal_chat.services.chat_avatar.get_chat_manager", return_value=mgr),
        patch("app.portal_chat.services.chat_avatar.async_delete_object", new_callable=AsyncMock) as dm,
    ):
        await chat_av.clear_group_chat_avatar(sqlite_session, admin, chat.id)

    dm.assert_not_called()
    mgr.publish.assert_not_called()


@pytest.mark.asyncio
async def test_save_group_avatar_partial_cleanup_delete_fails_logs_warning(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
    caplog: pytest.LogCaptureFixture,
) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Двойной сбой", member_subs=[user_portal_regular().sub]),
    )

    with (
        patch(
            "app.portal_chat.services.chat_avatar.async_upload_bytes_to_key",
            new_callable=AsyncMock,
            side_effect=RuntimeError("upload fail"),
        ),
        patch(
            "app.portal_chat.services.chat_avatar.async_delete_object",
            new_callable=AsyncMock,
            side_effect=OSError("cannot unlink partial"),
        ),
        caplog.at_level(logging.WARNING, logger="app.portal_chat.services.chat_avatar"),
    ):
        with pytest.raises(RuntimeError, match="upload fail"):
            await chat_av.save_group_chat_avatar(sqlite_session, admin, chat.id, file=_upload_jpeg())

    assert "частично загруженный" in caplog.text


@pytest.mark.asyncio
async def test_save_group_avatar_old_key_delete_failure_logs_warning(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
    caplog: pytest.LogCaptureFixture,
) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Старый ключ", member_subs=[user_portal_regular().sub]),
    )
    chat.avatar_storage_key = "avatars/chats/prev/gone.jpg"
    await sqlite_session.commit()
    await sqlite_session.refresh(chat)

    with (
        patch("app.portal_chat.services.chat_avatar.async_upload_bytes_to_key", new_callable=AsyncMock),
        patch(
            "app.portal_chat.services.chat_avatar.async_presign_avatar_url",
            new_callable=AsyncMock,
            return_value="https://ok",
        ),
        patch(
            "app.portal_chat.services.chat_avatar.async_delete_object",
            new_callable=AsyncMock,
            side_effect=OSError("minio busy"),
        ),
        caplog.at_level(logging.WARNING, logger="app.portal_chat.services.chat_avatar"),
    ):
        out = await chat_av.save_group_chat_avatar(sqlite_session, admin, chat.id, file=_upload_jpeg())

    assert out["avatar_url"] == "https://ok"
    assert "старый аватар" in caplog.text


@pytest.mark.asyncio
async def test_clear_group_avatar_delete_storage_logs_warning(
    sqlite_session: AsyncSession,
    _mock_chat_ws: object,
    caplog: pytest.LogCaptureFixture,
) -> None:
    admin = user_portal_admin()
    chat = await chat_svc.create_chat(
        sqlite_session,
        admin,
        PortalChatCreate(title="Удаление", member_subs=[user_portal_regular().sub]),
    )
    chat.avatar_storage_key = "avatars/chats/z/z.jpg"
    await sqlite_session.commit()

    with (
        patch(
            "app.portal_chat.services.chat_avatar.async_delete_object",
            new_callable=AsyncMock,
            side_effect=OSError("nfs stale"),
        ),
        caplog.at_level(logging.WARNING, logger="app.portal_chat.services.chat_avatar"),
    ):
        await chat_av.clear_group_chat_avatar(sqlite_session, admin, chat.id)

    assert "avatars/chats/z/z.jpg" in caplog.text
    await sqlite_session.refresh(chat)
    assert chat.avatar_storage_key is None


async def test_avatar_http_creator_ok_member_and_dm_forbidden(client_admin: AsyncClient) -> None:
    r_chat = await client_admin.post(
        f"{CHAT_API}/chats",
        json={"title": "Аватар HTTP", "member_subs": [user_portal_regular().sub]},
    )
    chat_id = r_chat.json()["id"]
    jpeg = ("a.jpg", BytesIO(b"\xff\xd8\xff\xe0"), "image/jpeg")
    with (
        patch("app.portal_chat.services.chat_avatar.async_upload_bytes_to_key", new_callable=AsyncMock),
        patch(
            "app.portal_chat.services.chat_avatar.async_presign_avatar_url",
            new_callable=AsyncMock,
            return_value="https://signed.example/g",
        ),
        patch("app.portal_chat.services.chat_avatar.async_delete_object", new_callable=AsyncMock),
        patch("app.portal_chat.services.chat_avatar.get_chat_manager", return_value=MagicMock(publish=AsyncMock())),
    ):
        r_ok = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/avatar", files={"file": jpeg})
        assert r_ok.status_code == 200, r_ok.text
        r_del = await client_admin.delete(f"{CHAT_API}/chats/{chat_id}/avatar")
        assert r_del.status_code == 204, r_del.text
    with as_user(user_portal_regular):
        r_mem = await client_admin.post(f"{CHAT_API}/chats/{chat_id}/avatar", files={"file": jpeg})
    assert_api_error(r_mem, 403, "forbidden")
    r_dm = await client_admin.post(f"{CHAT_API}/chats/direct", json={"other_user_sub": user_portal_regular().sub})
    dm_id = r_dm.json()["id"]
    r_dm_av = await client_admin.post(f"{CHAT_API}/chats/{dm_id}/avatar", files={"file": jpeg})
    assert_api_error(r_dm_av, 403, "forbidden")
