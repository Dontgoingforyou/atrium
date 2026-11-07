"""Общая валидация загружаемых файлов: whitelist MIME-типов + проверка magic bytes.

Используется там, где загружаются «обычные» файлы с whitelist по типу:
файлы задач (`portal_collab/services/task_file.py`). Вложения чата
(`portal_chat/services/attachment.py`) — осознанное исключение: по продуктовому решению
чат принимает файлы любых MIME-типов (см. комментарий в attachment.py), поэтому whitelist
там не применяется — используется только проверка magic bytes ниже (для известных форматов)
и лимит размера (Settings.attachment_max_size_bytes).

`check_magic_bytes` — единый источник проверки сигнатур для всех доменов (DRY, `dry.mdc`):
узкие whitelist'ы изображений в `app/services/avatar_upload_common.py` и
`app/services/rich_media_upload.py` (другие bounded context) вызывают эту же функцию с
`reject_unknown=True`, не заводят собственную копию словаря/цикла проверки байт.
"""

from __future__ import annotations

import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import BinaryIO, cast

from fastapi import UploadFile

from app.core.exceptions import ValidationError

# Крупнее этого порога SpooledTemporaryFile пишет на диск, а не держит тело в ОЗУ.
_UPLOAD_SPOOL_MAX_BYTES = 8 * 1024 * 1024
_UPLOAD_READ_CHUNK_BYTES = 64 * 1024

ALLOWED_GENERIC_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        # Документы
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/rtf",
        # Архивы
        "application/zip",
        "application/x-zip-compressed",
        "application/x-tar",
        "application/gzip",
        "application/x-7z-compressed",
        "application/x-rar-compressed",
        # Текст
        "text/plain",
        "text/csv",
        "text/markdown",
        # Видео
        "video/mp4",
        "video/quicktime",
        "video/webm",
        "video/x-msvideo",
        # Аудио
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "audio/webm",
        "audio/mp4",
        "audio/aac",
        # application/octet-stream исключён: слишком широкий тип — обходит whitelist
        # (любой файл можно загрузить, выставив этот MIME). Если нужно принять
        # нестандартный бинарный формат — добавлять конкретный MIME.
    }
)

# Magic-bytes: минимальный словарь сигнатур для проверки реального типа файла.
# Пары (offset, bytes): offset — смещение от начала файла, bytes — ожидаемые октеты.
# Ключ — MIME-тип из whitelist. Если MIME не в словаре, проверка пропускается (pass-through).
GENERIC_MAGIC_BYTES: dict[str, list[tuple[int, bytes]]] = {
    "image/jpeg": [(0, b"\xff\xd8\xff")],
    "image/png": [(0, b"\x89PNG\r\n\x1a\n")],
    "image/gif": [(0, b"GIF8")],
    "image/webp": [(0, b"RIFF"), (8, b"WEBP")],
    "application/pdf": [(0, b"%PDF-")],
    "application/zip": [(0, b"PK\x03\x04")],
    "application/x-zip-compressed": [(0, b"PK\x03\x04")],
    "application/x-7z-compressed": [(0, b"7z\xbc\xaf\x27\x1c")],
    "application/gzip": [(0, b"\x1f\x8b")],
    "video/mp4": [(4, b"ftyp")],
    "video/quicktime": [(4, b"ftyp"), (4, b"moov")],
    "video/webm": [(0, b"\x1a\x45\xdf\xa3")],
    "audio/webm": [(0, b"\x1a\x45\xdf\xa3")],
    "audio/ogg": [(0, b"OggS")],
    "audio/mpeg": [(0, b"ID3"), (0, b"\xff\xfb"), (0, b"\xff\xf3"), (0, b"\xff\xf2")],
    "audio/wav": [(0, b"RIFF"), (8, b"WAVE")],
    "audio/mp4": [(4, b"ftyp")],
}
GENERIC_MAGIC_READ_BYTES = 16  # сколько байт читать для проверки


def _size_limit_message(max_bytes: int) -> str:
    max_mb = max_bytes // (1024 * 1024)
    return f"Размер файла должен быть от 1 байта до {max_mb} МБ"


def assert_declared_size_within_limit(declared_size: int | None, max_bytes: int) -> None:
    """Отклонить загрузку до чтения тела, если клиент заявил размер больше лимита."""
    if isinstance(declared_size, int) and declared_size > max_bytes:
        raise ValidationError(_size_limit_message(max_bytes))


@asynccontextmanager
async def open_upload_stream(file: UploadFile, max_bytes: int) -> AsyncIterator[tuple[BinaryIO, int]]:
    """Поток тела и его размер без копии всего файла в ``bytes``.

    Заявленный размер больше лимита отсекается до чтения. Если размер известен,
    отдаётся ``file.file``: Starlette уже кладёт крупный multipart на диск.
    Если размер не заявлен, тело читается чанками во временный файл (в ОЗУ не
    больше 8 МиБ). Поток, созданный здесь, закрывается при выходе из контекста.
    """
    assert_declared_size_within_limit(file.size, max_bytes)
    declared = file.size
    if isinstance(declared, int) and declared > 0:
        file.file.seek(0)
        yield file.file, declared
        return

    spool = tempfile.SpooledTemporaryFile(max_size=_UPLOAD_SPOOL_MAX_BYTES)
    total = 0
    try:
        while True:
            chunk = await file.read(_UPLOAD_READ_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise ValidationError(_size_limit_message(max_bytes))
            spool.write(chunk)
        spool.seek(0)
        yield cast(BinaryIO, spool), total
    finally:
        spool.close()


def normalize_content_type(raw: str) -> str:
    """Нормализует Content-Type: браузер может передать параметры после «;» (например, codecs)."""
    return (raw or "").split(";", 1)[0].strip().lower()


def check_magic_bytes(
    header: bytes,
    content_type: str,
    *,
    magic_bytes: dict[str, list[tuple[int, bytes]]] | None = None,
    reject_unknown: bool = False,
) -> bool:
    """Проверить, что заголовочные байты соответствуют заявленному MIME-типу.

    ``magic_bytes`` — свой словарь сигнатур (по умолчанию :data:`GENERIC_MAGIC_BYTES`);
    вызывающие с более узким whitelist'ом (аватары, rich-media) передают тот же словарь,
    что и общий, — ключи для изображений (jpeg/png/gif/webp) идентичны везде.

    ``reject_unknown`` — поведение для MIME, которого нет в словаре: ``False`` (по умолчанию,
    как для `attachment.py` — принимает файлы любых типов) пропускает проверку; ``True``
    (аватары, rich-media — узкий whitelist известных типов) отвергает как несоответствие.
    """
    rules = (magic_bytes if magic_bytes is not None else GENERIC_MAGIC_BYTES).get(content_type)
    if rules is None:
        return not reject_unknown
    for offset, expected in rules:
        end = offset + len(expected)
        if len(header) >= end and header[offset:end] == expected:
            return True
    return False


__all__ = [
    "ALLOWED_GENERIC_CONTENT_TYPES",
    "GENERIC_MAGIC_BYTES",
    "GENERIC_MAGIC_READ_BYTES",
    "assert_declared_size_within_limit",
    "normalize_content_type",
    "check_magic_bytes",
]
