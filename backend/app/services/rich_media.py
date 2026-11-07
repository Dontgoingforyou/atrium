"""Доступ к изображениям rich-text: RBAC и presigned URL."""

from __future__ import annotations

import uuid
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.permissions import require_manager_or_admin
from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.infrastructure.storage.client import get_presigned_url
from app.portal_collab.services.task import get_task, user_can_edit_task, user_can_view_task
from app.portal_documents.services.portal_document_queries import ensure_user_can_read_document
from app.portal_specialists.services.board_shared import (
    ensure_specialist_card_visible,
    require_specialist_write_access,
)
from app.schemas.auth import UserPublic
from app.schemas.rich_media import RichMediaRead
from app.services.rich_media_upload import upload_rich_media_image

# Публичный путь API (без хоста) — маркер в HTML; клиент резолвит в presigned URL.
RICH_MEDIA_FILE_PATH_PREFIX = "/api/v1/portal/rich-media/"


def rich_media_file_path(media_id: uuid.UUID) -> str:
    return f"{RICH_MEDIA_FILE_PATH_PREFIX}{media_id}/file"


def rich_media_to_read(media: PortalRichMedia) -> RichMediaRead:
    return RichMediaRead(
        id=media.id,
        content_type=media.content_type,
        file_size=int(media.file_size),
        original_filename=media.original_filename,
        file_path=rich_media_file_path(media.id),
        download_url=build_download_url(media),
        created_at=media.created_at,
    )


def build_download_url(media: PortalRichMedia) -> str:
    settings = get_settings()
    return get_presigned_url(
        media.storage_key,
        ttl_seconds=settings.attachment_presign_ttl_seconds,
        filename=media.original_filename,
        # PDF открываем inline в браузере; картинки — тоже без force download.
        force_download=False,
    )


async def _get_media_row(session: AsyncSession, media_id: uuid.UUID) -> PortalRichMedia:
    result = await session.execute(select(PortalRichMedia).where(PortalRichMedia.id == media_id))
    media = result.scalar_one_or_none()
    if media is None:
        raise NotFoundError("Изображение не найдено")
    return media


async def _ensure_can_access_media(session: AsyncSession, user: UserPublic, media: PortalRichMedia) -> None:
    if media.task_id is not None:
        task = await get_task(session, user, media.task_id)
        if not await user_can_view_task(session, user, task):
            raise ForbiddenError("Нет доступа к изображению задачи")
        return
    if media.document_id is not None:
        # Читать изображение могут все, кто может читать сам документ
        # (загружать — только managers/admins, см. upload_document_rich_media).
        await ensure_user_can_read_document(session, user, media.document_id)
        return
    if media.specialist_sub is not None:
        require_manager_or_admin(user)
        profile = await session.get(PortalUserProfile, media.specialist_sub)
        if profile is None:
            raise NotFoundError("Изображение не найдено")
        await ensure_specialist_card_visible(session, profile)
        return
    raise ForbiddenError("Нет доступа к изображению")


async def upload_task_rich_media(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    *,
    file_data: BinaryIO,
    file_size: int,
    content_type: str,
    original_filename: str,
) -> PortalRichMedia:
    task = await get_task(session, user, task_id)
    if not await user_can_edit_task(session, user, task):
        raise ForbiddenError("Нет прав на редактирование задачи")
    media = await upload_rich_media_image(
        session,
        file_data=file_data,
        file_size=file_size,
        content_type=content_type,
        original_filename=original_filename,
        uploader_sub=user.sub,
        task_id=task_id,
    )
    await session.commit()
    return media


async def upload_document_rich_media(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
    *,
    file_data: BinaryIO,
    file_size: int,
    content_type: str,
    original_filename: str,
) -> PortalRichMedia:
    await ensure_user_can_read_document(session, user, document_id)
    require_manager_or_admin(user)
    media = await upload_rich_media_image(
        session,
        file_data=file_data,
        file_size=file_size,
        content_type=content_type,
        original_filename=original_filename,
        uploader_sub=user.sub,
        document_id=document_id,
    )
    await session.commit()
    return media


async def upload_specialist_rich_media(
    session: AsyncSession,
    user: UserPublic,
    specialist_sub: str,
    *,
    file_data: BinaryIO,
    file_size: int,
    content_type: str,
    original_filename: str,
) -> PortalRichMedia:
    await require_specialist_write_access(session, user, specialist_sub)
    profile = await session.get(PortalUserProfile, specialist_sub)
    if profile is None:
        raise NotFoundError("Пользователь не найден")
    await ensure_specialist_card_visible(session, profile)
    media = await upload_rich_media_image(
        session,
        file_data=file_data,
        file_size=file_size,
        content_type=content_type,
        original_filename=original_filename,
        uploader_sub=user.sub,
        specialist_sub=specialist_sub,
    )
    await session.commit()
    return media


async def get_rich_media_for_user(
    session: AsyncSession,
    user: UserPublic,
    media_id: uuid.UUID,
) -> PortalRichMedia:
    media = await _get_media_row(session, media_id)
    await _ensure_can_access_media(session, user, media)
    return media
