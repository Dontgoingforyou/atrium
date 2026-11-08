"""Вложения файлов документов портала (office/PDF/текст; без медиа — они в rich-text).

После успешного put в MinIO объект коммитится в БД; при ошибке commit ключ
удаляется best-effort (сироты без фоновой orphan-purge, в отличие от chat attachments).
"""

from __future__ import annotations

import logging
import uuid
from typing import BinaryIO

from minio.error import S3Error
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError, StorageUnavailableError, ValidationError
from app.core.permissions import require_manager_or_admin
from app.infrastructure.db.models.portal_document import PortalDocumentFile
from app.infrastructure.storage.client import (
    async_delete_object,
    async_delete_objects,
    async_upload_file,
    get_presigned_url,
)
from app.portal_documents.services.portal_document_queries import (
    document_subtree_ids,
    ensure_user_can_read_document,
)
from app.schemas.auth import UserPublic
from app.services.file_upload_validation import (
    GENERIC_MAGIC_READ_BYTES,
    check_magic_bytes,
    normalize_content_type,
)

logger = logging.getLogger(__name__)

# Документы (не фото/видео/аудио — те вставляются через rich-text).
ALLOWED_DOCUMENT_FILE_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/rtf",
        "text/plain",
        "text/csv",
        "text/markdown",
    }
)
# Список одного документа без PagedResponse: у экрана нет постранички.
_DOCUMENT_FILES_LIST_CAP = 500


def _validate_document_file_payload(
    *,
    file_data: BinaryIO,
    file_size: int,
    content_type: str,
    document_id: uuid.UUID | None,
    uploader_sub: str,
) -> str:
    settings = get_settings()
    if file_size <= 0 or file_size > settings.attachment_max_size_bytes:
        max_mb = settings.attachment_max_size_bytes // (1024 * 1024)
        raise ValidationError(f"Размер файла должен быть от 1 байта до {max_mb} МБ")

    normalized_ct = normalize_content_type(content_type)
    if normalized_ct not in ALLOWED_DOCUMENT_FILE_CONTENT_TYPES:
        logger.warning(
            "Отклонён тип файла при загрузке в документ: content_type=%s document_id=%s uploader_sub=%s",
            content_type,
            document_id,
            uploader_sub,
        )
        raise ValidationError("Допустимы документы: PDF, Word, Excel, PowerPoint, RTF, TXT, CSV, Markdown")

    header = file_data.read(GENERIC_MAGIC_READ_BYTES)
    file_data.seek(0)
    if not check_magic_bytes(header, normalized_ct):
        logger.warning(
            "Несоответствие magic bytes файла документа: заявлен %s, document_id=%s uploader_sub=%s",
            content_type,
            document_id,
            uploader_sub,
        )
        raise ValidationError("Содержимое файла не соответствует заявленному типу")
    return normalized_ct


async def _upload_to_storage(
    *,
    file_data: BinaryIO,
    file_size: int,
    content_type: str,
) -> str:
    try:
        return await async_upload_file(
            data=file_data,
            size=file_size,
            content_type=content_type,
        )
    except S3Error as exc:
        logger.exception("document_file: ошибка MinIO при upload")
        raise StorageUnavailableError("Хранилище файлов временно недоступно") from exc


async def _best_effort_delete_storage(storage_key: str) -> None:
    try:
        await async_delete_object(storage_key)
    except S3Error:
        logger.warning(
            "document_file: не удалось удалить сироту MinIO после ошибки БД storage_key=%s",
            storage_key,
            exc_info=True,
        )


async def list_files(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
) -> list[PortalDocumentFile]:
    """Список файлов-вложений документа. Доступ — как у просмотра документа."""
    await ensure_user_can_read_document(session, user, document_id)
    result = await session.execute(
        select(PortalDocumentFile)
        .where(PortalDocumentFile.document_id == document_id)
        .order_by(PortalDocumentFile.created_at)
        .limit(_DOCUMENT_FILES_LIST_CAP)
    )
    return list(result.scalars().all())


async def upload_file(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
    *,
    file_data: BinaryIO,
    file_size: int,
    content_type: str,
    original_filename: str,
) -> PortalDocumentFile:
    """Загружает файл в MinIO и прикрепляет к документу. Право — manager/admin."""
    await ensure_user_can_read_document(session, user, document_id)
    require_manager_or_admin(user)

    normalized_ct = _validate_document_file_payload(
        file_data=file_data,
        file_size=file_size,
        content_type=content_type,
        document_id=document_id,
        uploader_sub=user.sub,
    )

    storage_key = await _upload_to_storage(
        file_data=file_data,
        file_size=file_size,
        content_type=normalized_ct,
    )

    row = PortalDocumentFile(
        document_id=document_id,
        storage_key=storage_key,
        original_filename=original_filename[:512],
        content_type=normalized_ct[:128],
        file_size=file_size,
        uploaded_by_sub=user.sub,
    )
    session.add(row)
    try:
        await session.commit()
        await session.refresh(row)
    except Exception:
        await _best_effort_delete_storage(storage_key)
        raise

    logger.info(
        "Файл документа загружен: file_id=%s document_id=%s uploader=%s filename=%s size=%d",
        row.id,
        document_id,
        user.sub,
        original_filename,
        file_size,
    )
    return row


async def delete_file(
    session: AsyncSession,
    user: UserPublic,
    document_id: uuid.UUID,
    file_id: uuid.UUID,
) -> None:
    """Удалить вложение. Загрузивший, менеджер или portal_admin (после проверки чтения документа)."""
    await ensure_user_can_read_document(session, user, document_id)
    result = await session.execute(
        select(PortalDocumentFile).where(
            PortalDocumentFile.id == file_id,
            PortalDocumentFile.document_id == document_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("Файл не найден")
    if row.uploaded_by_sub != user.sub:
        try:
            require_manager_or_admin(user)
        except ForbiddenError:
            logger.warning(
                "Отказ в доступе: удаление чужого файла документа user_sub=%s document_id=%s file_id=%s",
                user.sub,
                document_id,
                file_id,
            )
            raise ForbiddenError(
                "Удалять файл может загрузивший его пользователь, менеджер или администратор"
            ) from None

    storage_key = row.storage_key
    await session.delete(row)
    await session.commit()
    try:
        await async_delete_object(storage_key)
    except S3Error as exc:
        logger.exception(
            "document_file: ошибка MinIO при удалении storage_key=%s (строка БД уже удалена)",
            storage_key,
        )
        raise StorageUnavailableError("Хранилище файлов временно недоступно") from exc


async def collect_storage_keys_for_documents(
    session: AsyncSession,
    document_ids: list[uuid.UUID],
) -> list[str]:
    """Ключи MinIO вложений для набора документов (purge)."""
    if not document_ids:
        return []
    rows = (
        (
            await session.execute(
                select(PortalDocumentFile.storage_key).where(PortalDocumentFile.document_id.in_(document_ids))
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def purge_storage_for_document_tree(session: AsyncSession, root_document_id: uuid.UUID) -> None:
    """Удаляет объекты MinIO для вложений поддерева документа (до delete из БД)."""
    tree_ids = await document_subtree_ids(session, root_document_id, include_deleted=True)
    keys = await collect_storage_keys_for_documents(session, tree_ids)
    if not keys:
        return
    try:
        await async_delete_objects(keys)
    except S3Error as exc:
        logger.exception(
            "document_file: ошибка MinIO при purge дерева document_id=%s",
            root_document_id,
        )
        raise StorageUnavailableError("Хранилище файлов временно недоступно") from exc


def build_download_url(file: PortalDocumentFile) -> str:
    return get_presigned_url(
        file.storage_key,
        filename=file.original_filename,
        force_download=True,
    )


def _view_response_content_type(content_type: str) -> str | None:
    """Для text/* отдаём charset=utf-8, иначе браузер часто ломает кириллицу в .md/.txt."""
    base = (content_type or "").split(";", 1)[0].strip().lower()
    if base.startswith("text/"):
        return f"{base}; charset=utf-8"
    return None


def build_view_url(file: PortalDocumentFile) -> str:
    return get_presigned_url(
        file.storage_key,
        filename=file.original_filename,
        force_download=False,
        response_content_type=_view_response_content_type(file.content_type),
    )
