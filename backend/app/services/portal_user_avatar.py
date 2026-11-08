"""Загрузка/удаление аватара пользователя через сервис профилей."""

from __future__ import annotations

import logging

import httpx
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, ServiceUnavailableError
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.integrations.profile_directory.client import ProfileDirectoryPhotoClient, PhotoMeta
from app.integrations.profile_directory.username import username_from_email
from app.schemas.portal_user import AvatarUploadRead
from app.services.avatar_upload_common import AVATAR_MAX_BYTES, read_and_validate_avatar_upload
from app.services.user_photo_meta_cache import set_cached_photo_meta
from app.services.user_photo_url import build_user_photo_proxy_url

logger = logging.getLogger(__name__)

__all__ = ["AVATAR_MAX_BYTES", "clear_user_avatar", "save_user_avatar"]


async def save_user_avatar(
    session: AsyncSession,
    *,
    user_sub: str,
    bearer_token: str,
    file: UploadFile,
    http: httpx.AsyncClient,
) -> AvatarUploadRead:
    """Загружает фото в EA ``/me/photo``; возвращает signed proxy URL."""
    settings = get_settings()
    if not settings.profile_directory_photos_enabled:
        raise ServiceUnavailableError("Загрузка аватара через сервис профилей не настроена")

    profile = await session.get(PortalUserProfile, user_sub)
    if profile is None:
        raise BadRequestError("Профиль пользователя не найден — выполните вход заново")

    validated = await read_and_validate_avatar_upload(file)
    client = ProfileDirectoryPhotoClient(settings, http)
    await client.upload_my_photo(
        bearer_token=bearer_token,
        file_name=file.filename or f"avatar{validated.ext}",
        content=validated.raw,
        content_type=validated.content_type,
    )
    version: int | None = None
    try:
        meta = await client.get_me_photo_meta(bearer_token=bearer_token)
        version = meta.version
        uname = username_from_email(profile.email)
        if uname:
            await set_cached_photo_meta(uname, meta)
    except Exception:
        logger.exception("Не удалось получить meta фото после upload sub=%s", user_sub)

    url = build_user_photo_proxy_url(user_sub=user_sub, email=profile.email, version=version)
    return AvatarUploadRead(avatar_url=url, avatar_focal_x=None, avatar_focal_y=None)


async def clear_user_avatar(
    session: AsyncSession,
    *,
    user_sub: str,
    bearer_token: str,
    http: httpx.AsyncClient,
) -> None:
    settings = get_settings()
    if not settings.profile_directory_photos_enabled:
        raise ServiceUnavailableError("Удаление аватара через сервис профилей не настроено")
    profile = await session.get(PortalUserProfile, user_sub)
    if profile is None:
        return
    client = ProfileDirectoryPhotoClient(settings, http)
    await client.delete_my_photo(bearer_token=bearer_token)
    uname = username_from_email(profile.email)
    if uname:
        await set_cached_photo_meta(uname, PhotoMeta(has_photo=False, version=None))
