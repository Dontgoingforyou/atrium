"""HTTP-клиент Effective Admin — фото сотрудников."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from app.core.config import Settings
from app.core.exceptions import NotFoundError, ServiceUnavailableError, ValidationError
from app.services.avatar_upload_common import AVATAR_MAX_BYTES
from app.services.file_upload_validation import GENERIC_MAGIC_READ_BYTES, check_magic_bytes, normalize_content_type

logger = logging.getLogger(__name__)

_EM_CLIENT_HEADER = "X-EM-Client"
_EM_CLIENT_LK = "effective-lk"
_PHOTO_ALLOWED_CT = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
_PHOTO_CT_ALIASES = {"image/jpg": "image/jpeg"}


def _canonical_photo_content_type(raw: str) -> str:
    """Нормализация CT EA: ``image/jpg`` → jpeg, magic bytes те же."""
    ct = normalize_content_type(raw)
    return _PHOTO_CT_ALIASES.get(ct, ct)


@dataclass(frozen=True)
class PhotoMeta:
    has_photo: bool
    version: int | None


@dataclass(frozen=True)
class PhotoBytes:
    content: bytes
    content_type: str


class EffectiveAdminPhotoClient:
    """Клиент ручек ``/api/v1/me/photo`` и ``/api/v1/users/{username}/photo``."""

    def __init__(self, settings: Settings, http: httpx.AsyncClient) -> None:
        self._settings = settings
        self._http = http
        self._base = settings.effective_admin_base_url.rstrip("/")

    def _require_enabled(self) -> None:
        if not self._settings.effective_admin_photos_enabled:
            raise ServiceUnavailableError("Интеграция фото Effective Admin не настроена")

    def _timeout(self) -> float:
        return self._settings.effective_admin_timeout_seconds

    async def get_me_photo_meta(self, *, bearer_token: str) -> PhotoMeta:
        self._require_enabled()
        url = f"{self._base}/api/v1/me/photo/meta"
        try:
            response = await self._http.get(
                url,
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=self._timeout(),
            )
        except httpx.RequestError as exc:
            logger.warning("EA photo meta: сетевой сбой %s", type(exc).__name__)
            raise ServiceUnavailableError("Effective Admin временно недоступен") from exc
        if response.status_code >= 400:
            logger.warning("EA photo meta → %s", response.status_code)
            raise ServiceUnavailableError("Effective Admin вернул ошибку")
        try:
            data: Any = response.json()
        except (ValueError, TypeError) as exc:
            raise ServiceUnavailableError("Effective Admin вернул ошибку") from exc
        if not isinstance(data, dict):
            raise ServiceUnavailableError("Effective Admin вернул ошибку")
        version = data.get("version")
        return PhotoMeta(
            has_photo=bool(data.get("has_photo")),
            version=version if isinstance(version, int) else None,
        )

    async def get_user_photo(self, *, username: str, bearer_token: str) -> PhotoBytes:
        self._require_enabled()
        safe = quote(username, safe="")
        url = f"{self._base}/api/v1/users/{safe}/photo"
        try:
            async with self._http.stream(
                "GET",
                url,
                headers={"Authorization": f"Bearer {bearer_token}"},
                timeout=self._timeout(),
            ) as response:
                if response.status_code == 404:
                    raise NotFoundError("Фото не найдено")
                if response.status_code >= 400:
                    logger.warning("EA photo get username=%s → %s", username, response.status_code)
                    raise ServiceUnavailableError("Effective Admin вернул ошибку")
                return await _read_validated_photo(response)
        except httpx.RequestError as exc:
            logger.warning("EA photo get: сетевой сбой username=%s %s", username, type(exc).__name__)
            raise ServiceUnavailableError("Effective Admin временно недоступен") from exc

    async def upload_my_photo(
        self,
        *,
        bearer_token: str,
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> None:
        self._require_enabled()
        url = f"{self._base}/api/v1/me/photo"
        try:
            response = await self._http.post(
                url,
                headers={
                    "Authorization": f"Bearer {bearer_token}",
                    _EM_CLIENT_HEADER: _EM_CLIENT_LK,
                },
                files={"file": (file_name, content, content_type)},
                timeout=self._timeout(),
            )
        except httpx.RequestError as exc:
            logger.warning("EA photo upload: сетевой сбой %s", type(exc).__name__)
            raise ServiceUnavailableError("Effective Admin временно недоступен") from exc
        if response.status_code == 422:
            raise ValidationError("Файл отклонён Effective Admin (формат или размер)")
        if response.status_code >= 400:
            logger.warning("EA photo upload → %s", response.status_code)
            raise ServiceUnavailableError("Effective Admin вернул ошибку при загрузке фото")

    async def delete_my_photo(self, *, bearer_token: str) -> None:
        self._require_enabled()
        url = f"{self._base}/api/v1/me/photo"
        try:
            response = await self._http.delete(
                url,
                headers={
                    "Authorization": f"Bearer {bearer_token}",
                    _EM_CLIENT_HEADER: _EM_CLIENT_LK,
                },
                timeout=self._timeout(),
            )
        except httpx.RequestError as exc:
            logger.warning("EA photo delete: сетевой сбой %s", type(exc).__name__)
            raise ServiceUnavailableError("Effective Admin временно недоступен") from exc
        if response.status_code >= 400 and response.status_code != 404:
            logger.warning("EA photo delete → %s", response.status_code)
            raise ServiceUnavailableError("Effective Admin вернул ошибку при удалении фото")


async def _read_validated_photo(response: httpx.Response) -> PhotoBytes:
    raw_len = response.headers.get("content-length")
    if raw_len is not None:
        try:
            if int(raw_len) > AVATAR_MAX_BYTES:
                raise ServiceUnavailableError("Effective Admin вернул слишком большой файл")
        except ValueError:
            pass
    chunks: list[bytes] = []
    total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > AVATAR_MAX_BYTES:
            raise ServiceUnavailableError("Effective Admin вернул слишком большой файл")
        chunks.append(chunk)
    raw = b"".join(chunks)
    ct = _canonical_photo_content_type(response.headers.get("content-type") or "")
    if ct not in _PHOTO_ALLOWED_CT:
        logger.warning("EA photo: недопустимый Content-Type %s", ct)
        raise ServiceUnavailableError("Effective Admin вернул недопустимый тип файла")
    if not check_magic_bytes(raw[:GENERIC_MAGIC_READ_BYTES], ct, reject_unknown=True):
        logger.warning("EA photo: magic bytes не соответствуют %s", ct)
        raise ServiceUnavailableError("Effective Admin вернул недопустимый тип файла")
    return PhotoBytes(content=raw, content_type=ct)
