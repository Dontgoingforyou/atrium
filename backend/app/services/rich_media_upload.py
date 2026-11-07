"""Валидация и загрузка изображений rich-text (общая для задач и документов)."""

from __future__ import annotations

import logging
import uuid
from typing import BinaryIO

from minio.error import S3Error
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import StorageUnavailableError, ValidationError
from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
from app.infrastructure.storage.client import async_upload_stream_to_key
from app.services.file_upload_validation import GENERIC_MAGIC_READ_BYTES, check_magic_bytes

logger = logging.getLogger(__name__)

_RICH_MEDIA_IMAGE_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    }
)


def _normalize_content_type(raw: str) -> str:
    base = (raw or "").split(";", 1)[0].strip().lower()
    return base or "application/octet-stream"


async def upload_rich_media_image(
    session: AsyncSession,
    *,
    file_data: BinaryIO,
    file_size: int,
    content_type: str,
    original_filename: str,
    uploader_sub: str,
    task_id: uuid.UUID | None = None,
    document_id: uuid.UUID | None = None,
    specialist_sub: str | None = None,
) -> PortalRichMedia:
    """Загружает изображение в MinIO и создаёт запись portal_rich_media."""
    parents = sum(value is not None for value in (task_id, document_id, specialist_sub))
    if parents != 1:
        raise ValidationError("Укажите ровно одну привязку: задачу, документ или специалиста")

    settings = get_settings()
    if file_size <= 0 or file_size > settings.attachment_max_size_bytes:
        max_mb = settings.attachment_max_size_bytes // (1024 * 1024)
        raise ValidationError(f"Размер файла превышает лимит {max_mb} МБ")

    normalized_type = _normalize_content_type(content_type)
    if normalized_type not in _RICH_MEDIA_IMAGE_TYPES:
        raise ValidationError("Допустимы только изображения JPEG, PNG, GIF или WebP")

    header = file_data.read(GENERIC_MAGIC_READ_BYTES)
    file_data.seek(0)
    if not check_magic_bytes(header, normalized_type, reject_unknown=True):
        logger.warning(
            "rich_media: несоответствие magic bytes (type=%s, uploader_sub=%s)",
            normalized_type,
            uploader_sub,
        )
        raise ValidationError("Содержимое файла не соответствует заявленному типу изображения")

    media_id = uuid.uuid4()
    safe_name = (original_filename or "image").replace("\\", "/").split("/")[-1].strip() or "image"
    safe_name = safe_name[:200]
    storage_key = f"rich-media/{media_id}/{safe_name}"

    try:
        await async_upload_stream_to_key(
            data=file_data,
            size=file_size,
            storage_key=storage_key,
            content_type=normalized_type,
        )
    except S3Error as exc:
        logger.exception("rich_media: ошибка MinIO при загрузке media_id=%s", media_id)
        raise StorageUnavailableError("Хранилище файлов временно недоступно") from exc

    row = PortalRichMedia(
        id=media_id,
        storage_key=storage_key,
        content_type=normalized_type,
        original_filename=original_filename or "image",
        file_size=file_size,
        uploader_sub=uploader_sub,
        task_id=task_id,
        document_id=document_id,
        specialist_sub=specialist_sub,
    )
    session.add(row)
    await session.flush()
    return row
