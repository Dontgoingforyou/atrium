from __future__ import annotations

import logging
import uuid
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.infrastructure.db.models.portal_task import PortalTaskFile
from app.infrastructure.storage.client import async_delete_object, async_upload_file, get_presigned_url
from app.portal_collab.services.task import get_task
from app.portal_collab.services.task_jira_schedule import schedule_file_jira_push
from app.schemas.auth import UserPublic
from app.services.file_upload_validation import (
    ALLOWED_GENERIC_CONTENT_TYPES,
    GENERIC_MAGIC_READ_BYTES,
    check_magic_bytes,
    normalize_content_type,
)

logger = logging.getLogger(__name__)


async def list_files(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
) -> list[PortalTaskFile]:
    """Список файлов задачи. Доступ — как у просмотра самой задачи."""
    await get_task(session, user, task_id)
    result = await session.execute(
        select(PortalTaskFile).where(PortalTaskFile.task_id == task_id).order_by(PortalTaskFile.created_at)
    )
    return list(result.scalars().all())


async def upload_file(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    *,
    file_data: BinaryIO,
    file_size: int,
    content_type: str,
    original_filename: str,
) -> PortalTaskFile:
    """Загружает файл в MinIO и прикрепляет его к задаче. Право — как у просмотра задачи."""
    await get_task(session, user, task_id)

    settings = get_settings()
    if file_size <= 0 or file_size > settings.attachment_max_size_bytes:
        max_mb = settings.attachment_max_size_bytes // (1024 * 1024)
        raise ValidationError(f"Размер файла должен быть от 1 байта до {max_mb} МБ")

    normalized_ct = normalize_content_type(content_type)
    if ALLOWED_GENERIC_CONTENT_TYPES and normalized_ct not in ALLOWED_GENERIC_CONTENT_TYPES:
        raise ValidationError(f"Тип файла не поддерживается: {content_type}")

    header = file_data.read(GENERIC_MAGIC_READ_BYTES)
    file_data.seek(0)
    if not check_magic_bytes(header, normalized_ct):
        logger.warning(
            "Несоответствие magic bytes при загрузке файла задачи: заявлен %s, task_id=%s uploader_sub=%s",
            normalized_ct,
            task_id,
            user.sub,
        )
        raise ValidationError(f"Содержимое файла не соответствует заявленному типу: {content_type}")

    storage_key = await async_upload_file(
        data=file_data,
        size=file_size,
        content_type=normalized_ct,
    )

    file = PortalTaskFile(
        task_id=task_id,
        storage_key=storage_key,
        original_filename=original_filename[:512],
        content_type=normalized_ct[:128],
        file_size=file_size,
        uploaded_by_sub=user.sub,
    )
    session.add(file)
    await session.commit()
    await session.refresh(file)
    schedule_file_jira_push(file.id)
    logger.info(
        "Файл задачи загружен: file_id=%s task_id=%s uploader=%s filename=%s size=%d",
        file.id,
        task_id,
        user.sub,
        original_filename,
        file_size,
    )
    return file


async def delete_file(
    session: AsyncSession,
    user: UserPublic,
    task_id: uuid.UUID,
    file_id: uuid.UUID,
) -> None:
    """Удалить файл. Право — только загрузивший файл или portal_admin."""
    await get_task(session, user, task_id)
    result = await session.execute(
        select(PortalTaskFile).where(
            PortalTaskFile.id == file_id,
            PortalTaskFile.task_id == task_id,
        )
    )
    file = result.scalar_one_or_none()
    if file is None:
        raise NotFoundError("Файл не найден")
    if file.uploaded_by_sub != user.sub and not user.is_portal_admin:
        logger.warning(
            "Отказ в доступе: удаление чужого файла задачи user_sub=%s task_id=%s file_id=%s",
            user.sub,
            task_id,
            file_id,
        )
        raise ForbiddenError("Удалять файл может только загрузивший его пользователь или администратор")

    storage_key = file.storage_key
    await session.delete(file)
    await session.commit()
    await async_delete_object(storage_key)


def build_download_url(file: PortalTaskFile) -> str:
    """Возвращает presigned URL для скачивания файла с Content-Disposition: attachment."""
    return get_presigned_url(
        file.storage_key,
        filename=file.original_filename,
        force_download=True,
    )


def build_view_url(file: PortalTaskFile) -> str:
    """Возвращает presigned URL для просмотра файла (без принудительного скачивания).

    Используется для инлайн-предпросмотра изображений/видео и открытия документов
    в новой вкладке браузера (без ``force_download`` браузер сам решает, отрисовать
    содержимое инлайн — картинку, видео, PDF — или скачать неизвестный формат).
    """
    return get_presigned_url(
        file.storage_key,
        filename=file.original_filename,
        force_download=False,
    )
