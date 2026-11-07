from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import BinaryIO

from minio.error import S3Error
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, NotFoundError, StorageUnavailableError, ValidationError
from app.infrastructure.db.models.portal_chat import PortalChatAttachment, PortalChatMessage
from app.infrastructure.storage.client import (
    async_delete_objects,
    async_upload_file,
    get_presigned_url,
)
from app.portal_chat.constants import VOICE_WAVEFORM_BARS
from app.portal_chat.services._queries import message_hidden_for_user
from app.services.file_upload_validation import (
    GENERIC_MAGIC_READ_BYTES as _MAGIC_READ_BYTES,
)
from app.services.file_upload_validation import (
    check_magic_bytes as _check_magic_bytes,
)

logger = logging.getLogger(__name__)


def parse_voice_waveform_json(raw: str | None) -> list[float] | None:
    """Разбирает waveform: ровно ``VOICE_WAVEFORM_BARS`` значений в [0, 1]. Иначе None."""
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("voice_waveform: некорректный JSON, игнорируем")
        return None
    if not isinstance(parsed, list) or len(parsed) != VOICE_WAVEFORM_BARS:
        logger.warning("voice_waveform: ожидается ровно %s значений, игнорируем", VOICE_WAVEFORM_BARS)
        return None
    out: list[float] = []
    for item in parsed:
        if not isinstance(item, (int, float)):
            logger.warning("voice_waveform: нечисловое значение, игнорируем")
            return None
        value = float(item)
        if value < 0.0 or value > 1.0:
            logger.warning("voice_waveform: значение вне [0, 1], игнорируем")
            return None
        out.append(value)
    return out


async def upload_attachment(
    session: AsyncSession,
    *,
    file_data: BinaryIO,
    file_size: int,
    content_type: str,
    original_filename: str,
    uploader_sub: str,
    chat_id: uuid.UUID,
    voice_duration_seconds: float | None = None,
    voice_waveform: list[float] | None = None,
) -> PortalChatAttachment:
    """Загружает файл в MinIO и создаёт запись в БД (message_id пока NULL).

    Вызывающий код обязан проверить, что uploader_sub — участник чата.

    ОСОЗНАННЫЙ КОМПРОМИСС ТРАНЗАКЦИЙ: файл сохраняется в MinIO и фиксируется в БД
    до привязки к сообщению, чтобы клиент мог получить attachment_id заранее. Если
    клиент не отправит сообщение — вложение останется «осиротевшим» (message_id=NULL).
    Для очистки используйте purge_orphan_attachments_older_than() и
    purge_attachments_linked_to_soft_deleted_messages().
    """
    settings = get_settings()

    if file_size <= 0 or file_size > settings.attachment_max_size_bytes:
        max_mb = settings.attachment_max_size_bytes // (1024 * 1024)
        raise ValidationError(f"Размер файла должен быть от 1 байта до {max_mb} МБ")

    # Нормализуем тип: браузер может передать «audio/webm;codecs=opus» — параметры после «;»
    # отрезаем перед сохранением (аналогично avatar_upload_common.py).
    # Whitelist MIME-типов здесь осознанно не применяется (в отличие от task_file.py):
    # продуктовое решение — в чат можно прикладывать файлы любых типов, защита — только
    # лимит размера выше и проверка magic bytes для известных форматов ниже.
    normalized_ct = content_type.split(";")[0].strip().lower()

    is_audio = normalized_ct.startswith("audio/")
    stored_duration = voice_duration_seconds if is_audio else None
    stored_waveform = voice_waveform if is_audio else None

    # Проверка magic bytes: читаем первые байты и сравниваем с ожидаемой сигнатурой.
    # file_data — BinaryIO; после чтения возвращаем указатель в начало.
    header = file_data.read(_MAGIC_READ_BYTES)
    file_data.seek(0)
    if not _check_magic_bytes(header, normalized_ct):
        logger.warning(
            "Несоответствие magic bytes: заявлен %s, но сигнатура не совпадает (uploader_sub=%s)",
            normalized_ct,
            uploader_sub,
        )
        raise ValidationError(f"Содержимое файла не соответствует заявленному типу: {content_type}")

    storage_key = await async_upload_file(
        data=file_data,
        size=file_size,
        content_type=normalized_ct,
    )

    attachment = PortalChatAttachment(
        chat_id=chat_id,
        uploader_sub=uploader_sub,
        original_filename=original_filename[:512],
        content_type=normalized_ct[:128],
        file_size=file_size,
        storage_key=storage_key,
        voice_duration_seconds=stored_duration,
        voice_waveform=stored_waveform,
    )
    session.add(attachment)
    await session.commit()
    await session.refresh(attachment)
    logger.info(
        "Вложение загружено: attachment_id=%s chat_id=%s uploader=%s filename=%s size=%d",
        attachment.id,
        chat_id,
        uploader_sub,
        original_filename,
        file_size,
    )
    return attachment


async def get_attachment_with_access_check(
    session: AsyncSession,
    attachment_id: uuid.UUID,
    viewer_sub: str,
    chat_id: uuid.UUID,
) -> PortalChatAttachment:
    """Возвращает вложение, проверяя принадлежность к чату (доступ к чату проверяет роутер)."""
    attachment = await session.get(PortalChatAttachment, attachment_id)
    if attachment is None or attachment.chat_id != chat_id:
        raise NotFoundError("Вложение не найдено")
    if attachment.message_id is not None and await message_hidden_for_user(session, viewer_sub, attachment.message_id):
        raise NotFoundError("Вложение не найдено")
    return attachment


def build_download_url(attachment: PortalChatAttachment) -> str:
    """Возвращает presigned URL для скачивания вложения с Content-Disposition: attachment."""
    return get_presigned_url(
        attachment.storage_key,
        filename=attachment.original_filename,
        force_download=True,
    )


async def link_attachments_to_message(
    session: AsyncSession,
    attachment_ids: list[uuid.UUID],
    message_id: uuid.UUID,
    chat_id: uuid.UUID,
    uploader_sub: str,
) -> list[PortalChatAttachment]:
    """Привязывает вложения к сообщению.

    Проверяет, что вложения принадлежат чату и загружены тем же пользователем,
    а также ещё не привязаны к другому сообщению.
    """
    if not attachment_ids:
        return []

    stmt = select(PortalChatAttachment).where(PortalChatAttachment.id.in_(attachment_ids))
    rows = list((await session.execute(stmt)).scalars().all())
    rows_by_id: dict[uuid.UUID, PortalChatAttachment] = {r.id: r for r in rows}

    for aid in attachment_ids:
        att = rows_by_id.get(aid)
        if att is None:
            raise NotFoundError(f"Вложение {aid} не найдено")
        if att.chat_id != chat_id:
            raise ForbiddenError("Вложение принадлежит другому чату")
        if att.uploader_sub != uploader_sub:
            raise ForbiddenError("Вложение загружено другим пользователем")
        if att.message_id is not None:
            raise ForbiddenError(f"Вложение {aid} уже привязано к сообщению")
        att.message_id = message_id

    await session.flush()
    return rows


async def purge_orphan_attachments_older_than(
    session: AsyncSession,
    *,
    min_age_hours: float,
) -> int:
    """Удаляет в MinIO и БД вложения без ``message_id`` старше порога (загрузили файл, не отправили).

    Возвращает число удалённых строк. При ошибке MinIO — ``StorageUnavailableError``.
    Использует batch-delete (до 1000 ключей за запрос) для снижения нагрузки на MinIO.
    """
    if min_age_hours <= 0:
        raise ValueError("min_age_hours должен быть положительным")
    cutoff = datetime.now(UTC) - timedelta(hours=min_age_hours)
    stmt = select(PortalChatAttachment).where(
        PortalChatAttachment.message_id.is_(None),
        PortalChatAttachment.created_at < cutoff,
    )
    rows = list((await session.execute(stmt)).scalars().all())
    if not rows:
        return 0

    try:
        await async_delete_objects([att.storage_key for att in rows])
    except S3Error as exc:
        logger.exception("MinIO batch-delete при очистке осиротевших вложений")
        raise StorageUnavailableError() from exc

    ids = [att.id for att in rows]
    await session.execute(delete(PortalChatAttachment).where(PortalChatAttachment.id.in_(ids)))
    await session.commit()
    return len(rows)


async def purge_attachments_linked_to_soft_deleted_messages(session: AsyncSession) -> int:
    """Удаляет в MinIO и БД вложения, привязанные к сообщениям с ``deleted_for_all_at`` (бэкфилл).

    Идемпотентно: повторный запуск безопасен (остаётся нечего удалять).
    Использует batch-delete (до 1000 ключей за запрос) для снижения нагрузки на MinIO.
    """
    stmt = (
        select(PortalChatAttachment)
        .join(PortalChatMessage, PortalChatAttachment.message_id == PortalChatMessage.id)
        .where(PortalChatMessage.deleted_for_all_at.is_not(None))
    )
    rows = list((await session.execute(stmt)).scalars().all())
    if not rows:
        return 0

    try:
        await async_delete_objects([att.storage_key for att in rows])
    except S3Error as exc:
        logger.exception("MinIO batch-delete при бэкфилле вложений soft-deleted сообщений")
        raise StorageUnavailableError() from exc

    ids = [att.id for att in rows]
    await session.execute(delete(PortalChatAttachment).where(PortalChatAttachment.id.in_(ids)))
    await session.commit()
    return len(rows)
