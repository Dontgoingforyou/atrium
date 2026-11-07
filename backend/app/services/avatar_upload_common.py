from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from uuid import UUID

from fastapi import UploadFile

from app.core.exceptions import BadRequestError, PayloadTooLargeError
from app.services.file_upload_validation import GENERIC_MAGIC_READ_BYTES, check_magic_bytes

AVATAR_MAX_BYTES = 20 * 1024 * 1024
# Читаем файл частями, а не всё тело сразу (security.mdc — вектор DoS при полном
# await file.read() до проверки размера): чанк должен быть меньше лимита, чтобы
# прерваться раньше, чем в память попадёт файл, ощутимо превышающий AVATAR_MAX_BYTES.
_READ_CHUNK_BYTES = 1024 * 1024

_ALLOWED_CT: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def clamp_focal_01(v: float) -> float:
    return max(0.0, min(1.0, v))


def storage_key_for_group_chat_avatar(chat_id: UUID, ext: str) -> str:
    safe = hashlib.sha256(str(chat_id).encode()).hexdigest()[:32]
    return f"avatars/chats/{safe}/{uuid.uuid4().hex}{ext}"


@dataclass(frozen=True)
class ValidatedAvatarUpload:
    """Результат проверки тела загрузки аватара."""

    raw: bytes
    content_type: str
    ext: str


async def _read_bounded(file: UploadFile, max_bytes: int) -> bytes:
    """Читает файл по частям, прерываясь сразу при превышении ``max_bytes``.

    В отличие от ``await file.read()`` не буферизует в памяти тело, гораздо большее
    заявленного лимита, — оценка размера идёт по ходу чтения, не постфактум
    (см. security.mdc, «Загрузка файлов»).
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            max_mb = max_bytes // (1024 * 1024)
            raise PayloadTooLargeError(f"Размер файла не более {max_mb} МБ")
        chunks.append(chunk)
    return b"".join(chunks)


async def read_and_validate_avatar_upload(
    file: UploadFile,
) -> ValidatedAvatarUpload:
    """Читает файл (потоково, с ранним прерыванием по размеру) и проверяет MIME; иначе ``AppError``."""
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct not in _ALLOWED_CT:
        raise BadRequestError("Допустимы только изображения JPEG, PNG, WebP и GIF")

    raw = await _read_bounded(file, AVATAR_MAX_BYTES)

    if not check_magic_bytes(raw[:GENERIC_MAGIC_READ_BYTES], ct, reject_unknown=True):
        raise BadRequestError("Содержимое файла не соответствует заявленному типу изображения")
    return ValidatedAvatarUpload(raw=raw, content_type=ct, ext=_ALLOWED_CT[ct])
