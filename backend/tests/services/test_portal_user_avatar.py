"""Тесты загрузки аватара через сервис профилей (клиент мокается)."""

from __future__ import annotations

from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from app.core.exceptions import AppError, BadRequestError, ServiceUnavailableError
from app.integrations.profile_directory.client import PhotoMeta
from app.services import portal_user_avatar as av_svc
from app.services.avatar_upload_common import AVATAR_MAX_BYTES
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession


def _upload_jpeg(data: bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 20, *, filename: str = "a.jpg") -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(data),
        headers={"content-type": "image/jpeg"},
    )


def _http() -> httpx.AsyncClient:
    return MagicMock(spec=httpx.AsyncClient)


@pytest.mark.asyncio
async def test_save_avatar_too_large_returns_413(sqlite_session: AsyncSession) -> None:
    big = b"x" * (AVATAR_MAX_BYTES + 1)
    with (
        patch("app.services.portal_user_avatar.get_settings") as gs,
        pytest.raises(AppError) as ei,
    ):
        gs.return_value.profile_directory_photos_enabled = True
        await av_svc.save_user_avatar(
            sqlite_session,
            user_sub="admin-sub",
            bearer_token="tok",
            file=_upload_jpeg(big),
            http=_http(),
        )
    assert ei.value.status_code == 413


@pytest.mark.asyncio
async def test_save_avatar_bad_content_type_returns_400(sqlite_session: AsyncSession) -> None:
    uf = UploadFile(
        filename="x.bin",
        file=BytesIO(b"data"),
        headers={"content-type": "application/octet-stream"},
    )
    with (
        patch("app.services.portal_user_avatar.get_settings") as gs,
        pytest.raises(AppError) as ei,
    ):
        gs.return_value.profile_directory_photos_enabled = True
        await av_svc.save_user_avatar(
            sqlite_session,
            user_sub="admin-sub",
            bearer_token="tok",
            file=uf,
            http=_http(),
        )
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_save_avatar_bad_magic_bytes_returns_400(sqlite_session: AsyncSession) -> None:
    uf = UploadFile(
        filename="fake.jpg",
        file=BytesIO(b"not-a-jpeg"),
        headers={"content-type": "image/jpeg"},
    )
    with (
        patch("app.services.portal_user_avatar.get_settings") as gs,
        pytest.raises(BadRequestError, match="Содержимое"),
    ):
        gs.return_value.profile_directory_photos_enabled = True
        await av_svc.save_user_avatar(
            sqlite_session,
            user_sub="admin-sub",
            bearer_token="tok",
            file=uf,
            http=_http(),
        )


@pytest.mark.asyncio
async def test_save_avatar_unknown_profile_returns_400(sqlite_session: AsyncSession) -> None:
    with (
        patch("app.services.portal_user_avatar.get_settings") as gs,
        pytest.raises(BadRequestError) as ei,
    ):
        gs.return_value.profile_directory_photos_enabled = True
        await av_svc.save_user_avatar(
            sqlite_session,
            user_sub="no-such-sub-xyz",
            bearer_token="tok",
            file=_upload_jpeg(),
            http=_http(),
        )
    assert ei.value.status_code == 400


@pytest.mark.asyncio
async def test_save_avatar_disabled_returns_503(sqlite_session: AsyncSession) -> None:
    with (
        patch("app.services.portal_user_avatar.get_settings") as gs,
        pytest.raises(ServiceUnavailableError),
    ):
        gs.return_value.profile_directory_photos_enabled = False
        await av_svc.save_user_avatar(
            sqlite_session,
            user_sub="admin-sub",
            bearer_token="tok",
            file=_upload_jpeg(),
            http=_http(),
        )


@pytest.mark.asyncio
async def test_save_avatar_success_calls_ea_and_caches_meta(sqlite_session: AsyncSession) -> None:
    client = MagicMock()
    client.upload_my_photo = AsyncMock()
    client.get_me_photo_meta = AsyncMock(return_value=PhotoMeta(has_photo=True, version=42))
    with (
        patch("app.services.portal_user_avatar.get_settings") as gs,
        patch("app.services.portal_user_avatar.ProfileDirectoryPhotoClient", return_value=client),
        patch(
            "app.services.portal_user_avatar.build_user_photo_proxy_url",
            return_value="/api/v1/portal/users/admin-sub/photo?exp=1&sig=x",
        ),
        patch("app.services.portal_user_avatar.set_cached_photo_meta", new=AsyncMock()) as mock_cache,
    ):
        gs.return_value.profile_directory_photos_enabled = True
        out = await av_svc.save_user_avatar(
            sqlite_session,
            user_sub="admin-sub",
            bearer_token="tok",
            file=_upload_jpeg(),
            http=_http(),
        )
    assert out.avatar_url and out.avatar_url.startswith("/api/v1/portal/users/")
    client.upload_my_photo.assert_awaited_once()
    mock_cache.assert_awaited_once()
    assert mock_cache.await_args.args[1].has_photo is True


@pytest.mark.asyncio
async def test_clear_avatar_calls_ea_and_invalidates_cache(sqlite_session: AsyncSession) -> None:
    client = MagicMock()
    client.delete_my_photo = AsyncMock()
    with (
        patch("app.services.portal_user_avatar.get_settings") as gs,
        patch("app.services.portal_user_avatar.ProfileDirectoryPhotoClient", return_value=client),
        patch("app.services.portal_user_avatar.set_cached_photo_meta", new=AsyncMock()) as mock_cache,
    ):
        gs.return_value.profile_directory_photos_enabled = True
        await av_svc.clear_user_avatar(
            sqlite_session,
            user_sub="admin-sub",
            bearer_token="tok",
            http=_http(),
        )
    client.delete_my_photo.assert_awaited_once()
    mock_cache.assert_awaited_once()
    assert mock_cache.await_args.args[1].has_photo is False


@pytest.mark.asyncio
async def test_clear_avatar_unknown_profile_is_noop(sqlite_session: AsyncSession) -> None:
    client = MagicMock()
    client.delete_my_photo = AsyncMock()
    with (
        patch("app.services.portal_user_avatar.get_settings") as gs,
        patch("app.services.portal_user_avatar.ProfileDirectoryPhotoClient", return_value=client),
    ):
        gs.return_value.profile_directory_photos_enabled = True
        await av_svc.clear_user_avatar(
            sqlite_session,
            user_sub="no-such-sub-xyz",
            bearer_token="tok",
            http=_http(),
        )
    client.delete_my_photo.assert_not_called()
