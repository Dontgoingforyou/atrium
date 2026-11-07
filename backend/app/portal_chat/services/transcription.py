"""Транскрибация голосовых сообщений чата через OpenAI Whisper."""

from __future__ import annotations

import io
import logging
import uuid

from openai import AsyncOpenAI, OpenAIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError, ValidationError
from app.infrastructure.db.models.portal_chat import PortalChatAttachment
from app.infrastructure.storage.client import async_download_object_bytes
from app.portal_chat.services._queries import ensure_chat_write_access
from app.portal_chat.services.attachment import get_attachment_with_access_check
from app.schemas.auth import UserPublic
from app.services.file_upload_validation import GENERIC_MAGIC_READ_BYTES, check_magic_bytes
from app.services.openai_client import build_openai_client

logger = logging.getLogger(__name__)


def _get_client() -> AsyncOpenAI:
    """Singleton AsyncOpenAI клиент (ленивая инициализация), общий конструктор — ``services/openai_client.py``."""
    s = get_settings()
    if not s.openai_api_key:
        raise ServiceUnavailableError("Транскрибация недоступна: не задан OPENAI_API_KEY")
    return build_openai_client(
        api_key=s.openai_api_key,
        base_url=s.openai_base_url,
        timeout=s.openai_whisper_timeout_seconds,
    )


_client: AsyncOpenAI | None = None


def _client_singleton() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = _get_client()
    return _client


def _is_voice_attachment(attachment: PortalChatAttachment) -> bool:
    ct = (attachment.content_type or "").split(";", 1)[0].strip().lower()
    return ct.startswith("audio/") and attachment.voice_duration_seconds is not None


async def transcribe_voice_attachment(
    session: AsyncSession,
    user: UserPublic,
    chat_id: uuid.UUID,
    attachment_id: uuid.UUID,
) -> PortalChatAttachment:
    """Скачивает голосовое вложение из MinIO и транскрибирует его через OpenAI Whisper.

    Результат сохраняется в ``voice_transcript`` и переиспользуется при повторном вызове
    (не дёргаем внешний API повторно, если транскрипт уже есть).
    """
    await ensure_chat_write_access(session, user, chat_id)
    attachment = await get_attachment_with_access_check(session, attachment_id, user.sub, chat_id)

    if not _is_voice_attachment(attachment):
        raise ValidationError("Транскрибация доступна только для голосовых сообщений")

    if attachment.voice_transcript:
        return attachment

    settings = get_settings()
    if attachment.file_size > settings.chat_whisper_max_size_bytes:
        max_mb = settings.chat_whisper_max_size_bytes // (1024 * 1024)
        raise ValidationError(f"Голосовое сообщение слишком большое для транскрибации (лимит {max_mb} МБ)")
    if not settings.openai_api_key:
        raise ServiceUnavailableError("Транскрибация недоступна: не задан OPENAI_API_KEY")

    audio_bytes = await async_download_object_bytes(attachment.storage_key)
    header = audio_bytes[:GENERIC_MAGIC_READ_BYTES]
    if not check_magic_bytes(header, attachment.content_type):
        raise ValidationError("Содержимое файла не соответствует заявленному аудиотипу")

    file_obj = io.BytesIO(audio_bytes)
    file_obj.name = attachment.original_filename or "voice.webm"

    try:
        client = _client_singleton()
        response = await client.audio.transcriptions.create(
            model=settings.openai_whisper_model,
            file=file_obj,
        )
    except OpenAIError as exc:
        logger.exception(
            "Ошибка OpenAI Whisper при транскрибации attachment_id=%s chat_id=%s",
            attachment_id,
            chat_id,
        )
        raise ServiceUnavailableError("Не удалось транскрибировать голосовое сообщение") from exc

    attachment.voice_transcript = response.text.strip()
    await session.commit()
    await session.refresh(attachment)
    logger.info("Транскрибировано голосовое сообщение attachment_id=%s chat_id=%s", attachment_id, chat_id)
    return attachment
