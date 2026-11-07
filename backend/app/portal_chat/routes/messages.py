from __future__ import annotations

import logging
import tempfile
import uuid
from typing import Annotated, BinaryIO, Literal, cast

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, Response, UploadFile

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.core.config import get_settings
from app.core.exceptions import PayloadTooLargeError
from app.infrastructure.db.models.portal_chat import PortalChat
from app.portal_chat.rate_limits import (
    enforce_chat_attachment_upload_limit,
    enforce_chat_message_post_limit,
    enforce_chat_transcribe_limit,
)
from app.portal_chat.schemas.chat import (
    AttachmentRead,
    MessageReactorItem,
    MessageReactorsResponse,
    MessageReaderItem,
    MessageReadersResponse,
    PortalChatMessageCreate,
    PortalChatMessageForward,
    PortalChatMessageReactionToggle,
    PortalChatMessageRead,
    PortalChatMessageUpdate,
)
from app.portal_chat.services import attachment as att_svc
from app.portal_chat.services import chat as svc
from app.portal_chat.services._queries import _is_orphan_non_dm_group_chat_row
from app.portal_chat.services._queries_messages import attachment_to_read
from app.portal_chat.services.inbox_preview import build_inbox_preview_text
from app.portal_chat.services.web_push import send_chat_message_web_push_bg
from app.portal_search.services import embedding as emb_svc
from app.portal_search.services.entity_text import chat_message_meta, chat_message_to_text
from app.schemas.pagination import PagedResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portal", tags=["Чаты"])

_UPLOAD_SPOOL_MAX = 8 * 1024 * 1024
_UPLOAD_CHUNK = 64 * 1024


async def _prepare_upload_stream(file: UploadFile, max_bytes: int) -> tuple[BinaryIO, int]:
    """Стримит upload с потолком размера; не читает весь файл в RAM заранее."""
    file_size = file.size
    if isinstance(file_size, int) and file_size > 0:
        if file_size > max_bytes:
            raise PayloadTooLargeError("Файл превышает допустимый размер")
        return file.file, file_size

    spool = tempfile.SpooledTemporaryFile(max_size=_UPLOAD_SPOOL_MAX)
    total = 0
    try:
        while True:
            chunk = await file.read(_UPLOAD_CHUNK)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise PayloadTooLargeError("Файл превышает допустимый размер")
            spool.write(chunk)
        spool.seek(0)
    except Exception:
        spool.close()
        raise
    return cast(BinaryIO, spool), total


def _schedule_chat_web_push(
    bg: BackgroundTasks,
    chat_id: uuid.UUID,
    msg: object,
    chat_row: PortalChat | None,
) -> None:
    """Фоновая отправка Web Push (если настроены VAPID и есть подписки)."""
    linked = getattr(msg, "__dict__", {}).get("attachments") or []
    body = getattr(msg, "body", None) or ""
    author_sub = str(getattr(msg, "author_sub", ""))
    message_id: uuid.UUID | None = getattr(msg, "id", None)
    mention_subs: list[str] = list(getattr(msg, "mentions", None) or [])
    preview = build_inbox_preview_text(
        body=body,
        attachment_content_types=[getattr(a, "content_type", "") for a in linked],
    )
    title_stripped = (chat_row.title or "").strip() if chat_row else ""
    chat_title = title_stripped or None
    is_direct = bool(chat_row and chat_row.canonical_dm_key)
    bg.add_task(
        send_chat_message_web_push_bg,
        chat_id,
        author_sub,
        preview,
        chat_title,
        is_direct,
        message_id,
        mention_subs,
    )


def _schedule_embedding(
    bg: BackgroundTasks,
    chat_row: PortalChat | None,
    msg_id: uuid.UUID,
    body: str,
    chat_id: uuid.UUID,
    author_sub: str,
) -> None:
    """Планирует фоновое обновление эмбеддинга для индексируемых чатов с непустым телом."""
    if chat_row and body and body.strip() and not _is_orphan_non_dm_group_chat_row(chat_row):
        bg.add_task(
            emb_svc.upsert_embedding_bg,
            "chat_message",
            str(msg_id),
            chat_message_to_text(body),
            chat_message_meta(chat_id=str(chat_id), author_sub=author_sub),
        )


@router.get(
    "/chats/{chat_id}/messages",
    summary="История сообщений чата",
    response_model=list[PortalChatMessageRead],
)
async def list_messages(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    around_message_id: Annotated[
        uuid.UUID | None,
        Query(
            description="Окно истории вокруг сообщения (диплинк); при задании skip игнорируется",
        ),
    ] = None,
) -> list[PortalChatMessageRead]:
    msgs = await svc.list_messages(
        db,
        user,
        chat_id,
        skip=skip if around_message_id is None else 0,
        limit=limit,
        around_message_id=around_message_id,
    )
    return await svc.messages_to_read_for_viewer(db, user, chat_id, msgs)


@router.post(
    "/chats/{chat_id}/messages",
    summary="Отправить сообщение",
    response_model=PortalChatMessageRead,
    status_code=201,
)
async def post_message(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalChatMessageCreate,
    bg: BackgroundTasks,
) -> PortalChatMessageRead:
    await enforce_chat_message_post_limit(user.sub, chat_id)
    msg = await svc.post_message(db, user, chat_id, body)
    members = await svc.list_chat_members(db, chat_id)
    chat_row = await db.get(PortalChat, chat_id)
    _schedule_embedding(bg, chat_row, msg.id, msg.body or "", chat_id, msg.author_sub)
    _schedule_chat_web_push(bg, chat_id, msg, chat_row)
    return svc.message_to_read_for_viewer(msg, user.sub, members)


@router.post(
    "/chats/{chat_id}/messages/forward",
    summary="Переслать сообщение из другого чата",
    response_model=PortalChatMessageRead,
    status_code=201,
)
async def post_forward_message(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalChatMessageForward,
    bg: BackgroundTasks,
) -> PortalChatMessageRead:
    await enforce_chat_message_post_limit(user.sub, chat_id)
    msg = await svc.forward_chat_message(db, user, chat_id, body.from_chat_id, body.message_id)
    members = await svc.list_chat_members(db, chat_id)
    chat_row = await db.get(PortalChat, chat_id)
    _schedule_embedding(bg, chat_row, msg.id, msg.body or "", chat_id, msg.author_sub)
    _schedule_chat_web_push(bg, chat_id, msg, chat_row)
    return svc.message_to_read_for_viewer(msg, user.sub, members)


@router.patch(
    "/chats/{chat_id}/messages/{message_id}",
    summary="Редактировать своё сообщение",
    response_model=PortalChatMessageRead,
)
async def patch_message(
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalChatMessageUpdate,
    bg: BackgroundTasks,
) -> PortalChatMessageRead:
    msg = await svc.update_message(db, user, chat_id, message_id, body)
    members = await svc.list_chat_members(db, chat_id)
    chat_row = await db.get(PortalChat, chat_id)
    _schedule_embedding(bg, chat_row, msg.id, msg.body or "", chat_id, msg.author_sub)
    return svc.message_to_read_for_viewer(msg, user.sub, members)


@router.post(
    "/chats/{chat_id}/messages/{message_id}/reactions",
    summary="Добавить или снять реакцию (toggle)",
    response_model=PortalChatMessageRead,
)
async def toggle_message_reaction(
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalChatMessageReactionToggle,
) -> PortalChatMessageRead:
    msg = await svc.toggle_message_reaction(db, user, chat_id, message_id, body.emoji)
    members = await svc.list_chat_members(db, chat_id)
    return svc.message_to_read_for_viewer(msg, user.sub, members)


@router.get(
    "/chats/{chat_id}/messages/pinned",
    summary="Список закреплённых сообщений чата",
    response_model=list[PortalChatMessageRead],
)
async def list_pinned_messages_route(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> list[PortalChatMessageRead]:
    msgs = await svc.list_pinned_messages(db, user, chat_id)
    members = await svc.list_chat_members(db, chat_id)
    return [svc.message_to_read_for_viewer(m, user.sub, members) for m in msgs]


@router.post(
    "/chats/{chat_id}/messages/{message_id}/pin",
    summary="Закрепить сообщение",
    response_model=PortalChatMessageRead,
)
async def pin_message_route(
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalChatMessageRead:
    msg = await svc.pin_message(db, user, chat_id, message_id)
    members = await svc.list_chat_members(db, chat_id)
    return svc.message_to_read_for_viewer(msg, user.sub, members)


@router.delete(
    "/chats/{chat_id}/messages/{message_id}/pin",
    summary="Открепить сообщение",
    response_model=PortalChatMessageRead,
)
async def unpin_message_route(
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalChatMessageRead:
    msg = await svc.unpin_message(db, user, chat_id, message_id)
    members = await svc.list_chat_members(db, chat_id)
    return svc.message_to_read_for_viewer(msg, user.sub, members)


@router.delete(
    "/chats/{chat_id}/messages/{message_id}",
    summary="Удалить сообщение (только у себя или у всех)",
    status_code=204,
    response_class=Response,
)
async def delete_message(
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    bg: BackgroundTasks,
    scope: Literal["me", "all"] = Query(..., description="me — скрыть у меня, all — удалить у всех (только автор)"),
) -> None:
    if scope == "me":
        await svc.delete_message_for_user(db, user, chat_id, message_id)
    else:
        await svc.delete_message_for_all(db, user, chat_id, message_id)
        bg.add_task(emb_svc.delete_embedding_bg, "chat_message", str(message_id))


@router.post(
    "/chats/{chat_id}/attachments",
    summary="Загрузить файловое вложение (до отправки сообщения)",
    response_model=AttachmentRead,
    status_code=201,
)
async def upload_chat_attachment(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(
        ..., description="Прикрепляемый файл (любой тип, лимит — Settings.attachment_max_size_bytes)"
    ),
    voice_duration_seconds: Annotated[
        float | None,
        Form(description="Длительность голосового сообщения в секундах (только для аудио)"),
    ] = None,
    voice_waveform_json: Annotated[
        str | None,
        Form(
            alias="voice_waveform",
            description="JSON-массив из 28 нормализованных значений амплитуды (0.0–1.0)",
        ),
    ] = None,
) -> AttachmentRead:
    """Загружает файл в MinIO и возвращает attachment_id.

    Используйте полученный ``attachment_id`` в поле ``attachment_ids`` при отправке сообщения
    (``POST /portal/chats/{chat_id}/messages``).
    """
    await svc.ensure_chat_write_access(db, user, chat_id)
    await enforce_chat_attachment_upload_limit(user.sub)

    voice_waveform = att_svc.parse_voice_waveform_json(voice_waveform_json)
    max_bytes = get_settings().attachment_max_size_bytes
    file_data, file_size = await _prepare_upload_stream(file, max_bytes)
    owns_stream = file_data is not file.file
    try:
        attachment = await att_svc.upload_attachment(
            db,
            file_data=file_data,
            file_size=file_size,
            content_type=file.content_type or "application/octet-stream",
            original_filename=file.filename or "file",
            uploader_sub=user.sub,
            chat_id=chat_id,
            voice_duration_seconds=voice_duration_seconds,
            voice_waveform=voice_waveform,
        )
    finally:
        if owns_stream:
            file_data.close()
    download_url = att_svc.build_download_url(attachment)
    return attachment_to_read(attachment, str(download_url))


@router.get(
    "/chats/{chat_id}/attachments/{attachment_id}/download",
    summary="Получить presigned URL для скачивания вложения",
    response_model=AttachmentRead,
)
async def get_attachment_download(
    chat_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> AttachmentRead:
    """Возвращает актуальный presigned URL для скачивания вложения."""
    await svc.ensure_chat_read_access(db, user, chat_id)
    attachment = await att_svc.get_attachment_with_access_check(db, attachment_id, user.sub, chat_id)
    download_url = att_svc.build_download_url(attachment)
    return attachment_to_read(attachment, str(download_url))


@router.post(
    "/chats/{chat_id}/attachments/{attachment_id}/transcribe",
    summary="Транскрибировать голосовое сообщение (OpenAI Whisper)",
    response_model=AttachmentRead,
)
async def transcribe_chat_attachment(
    chat_id: uuid.UUID,
    attachment_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> AttachmentRead:
    """Транскрибирует голосовое вложение в текст и сохраняет результат в ``transcript``."""
    await enforce_chat_transcribe_limit(user.sub)
    attachment = await svc.transcribe_voice_attachment(db, user, chat_id, attachment_id)
    download_url = att_svc.build_download_url(attachment)
    return attachment_to_read(attachment, str(download_url))


@router.get(
    "/chats/{chat_id}/attachments",
    summary="Галерея вложений чата (постранично)",
    response_model=PagedResponse[AttachmentRead],
)
async def list_chat_attachments_route(
    chat_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    kind: Annotated[
        Literal["media", "audio", "file"] | None,
        Query(description="Фильтр по типу вложения (media = фото/видео); без фильтра — все типы"),
    ] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> PagedResponse[AttachmentRead]:
    """Список вложений чата, привязанных к сообщениям (для отдельной галереи вложений)."""
    attachments, total = await svc.list_chat_attachments(db, user, chat_id, kind=kind, skip=skip, limit=limit)
    items = [attachment_to_read(att, att_svc.build_download_url(att)) for att in attachments]
    return PagedResponse(items=items, total=total, skip=skip, limit=limit)


@router.get(
    "/chats/{chat_id}/messages/{message_id}/readers",
    response_model=MessageReadersResponse,
    summary="Кто прочитал сообщение",
)
async def get_message_readers_route(
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
) -> MessageReadersResponse:
    """Список участников чата, у которых last_read_at >= created_at сообщения.

    Автор сообщения в список не включается. Доступен только участникам чата.
    """
    members = await svc.get_message_readers(db, user, chat_id, message_id)
    return MessageReadersResponse(
        message_id=message_id,
        readers=[
            MessageReaderItem(user_sub=m.user_sub, read_at=m.last_read_at)  # type: ignore[arg-type]
            for m in members
        ],
    )


@router.get(
    "/chats/{chat_id}/messages/{message_id}/reactions/reactors",
    response_model=MessageReactorsResponse,
    summary="Кто поставил реакцию",
)
async def get_message_reaction_reactors_route(
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    emoji: Annotated[str, Query(min_length=1, max_length=32, description="Эмодзи реакции")],
) -> MessageReactorsResponse:
    """Список пользователей, поставивших реакцию с данным эмодзи.

    Набор ограничен участниками чата — без PagedResponse (как у readers).
    """
    rows = await svc.get_message_reaction_reactors(db, user, chat_id, message_id, emoji)
    return MessageReactorsResponse(
        message_id=message_id,
        emoji=emoji.strip(),
        reactors=[MessageReactorItem(user_sub=r.user_sub, reacted_at=r.created_at) for r in rows],
    )
