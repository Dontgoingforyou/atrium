from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import timedelta
from functools import lru_cache
from io import BytesIO
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from app.core.config import get_settings
from app.core.exceptions import StorageUnavailableError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_minio_client() -> Minio:
    """Синглтон Minio-клиента (создаётся при первом вызове).

    Используется для операций записи/удаления объектов (внутренний endpoint).
    """
    settings = get_settings()
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_internal_secure,
    )


@lru_cache(maxsize=1)
def _get_minio_public_client() -> Minio:
    """Minio-клиент для генерации presigned URL с публичным endpoint.

    Регион получается через внутренний клиент (``minio_endpoint``), чтобы не делать
    HTTP-запросов к публичному endpoint изнутри контейнера. Когда регион задан явно
    в конструкторе, SDK пропускает region discovery и сразу подписывает URL.
    """
    settings = get_settings()
    public_ep = settings.minio_public_endpoint.strip() or settings.minio_endpoint.strip()
    region = get_minio_client()._get_region(settings.minio_bucket)
    return Minio(
        endpoint=public_ep,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
        region=region,
    )


def ensure_bucket_exists(bucket: str) -> None:
    """Создаёт бакет, если он ещё не существует. Вызывать при старте приложения."""
    client = get_minio_client()
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("MinIO: бакет '%s' создан", bucket)
    except S3Error as exc:
        logger.error("MinIO: ошибка при проверке/создании бакета '%s': %s", bucket, exc)
        raise


def upload_file(
    *,
    data: BinaryIO,
    size: int,
    content_type: str,
    bucket: str | None = None,
) -> str:
    """Загружает файл в MinIO, возвращает storage_key.

    Ключ строится как ``<uuid4>`` без предсказуемого пути — исключает
    угадывание URL при отключённых presigned URL.
    """
    settings = get_settings()
    _bucket = bucket or settings.minio_bucket
    client = get_minio_client()
    key = str(uuid.uuid4())
    client.put_object(
        bucket_name=_bucket,
        object_name=key,
        data=data,
        length=size,
        content_type=content_type,
    )
    logger.debug("MinIO: загружен объект bucket=%s key=%s size=%d", _bucket, key, size)
    return key


def upload_stream_to_key(
    *,
    data: BinaryIO,
    size: int,
    storage_key: str,
    content_type: str,
    bucket: str | None = None,
) -> str:
    """Загружает поток по фиксированному ключу, не буферизуя тело в памяти."""
    settings = get_settings()
    _bucket = bucket or settings.minio_bucket
    client = get_minio_client()
    client.put_object(
        bucket_name=_bucket,
        object_name=storage_key,
        data=data,
        length=size,
        content_type=content_type,
    )
    logger.debug("MinIO: загружен объект bucket=%s key=%s size=%d", _bucket, storage_key, size)
    return storage_key


def upload_bytes_to_key(
    *,
    data: bytes,
    storage_key: str,
    content_type: str,
    bucket: str | None = None,
) -> str:
    """Загружает объект по фиксированному ключу (аватары, предсказуемые пути)."""
    return upload_stream_to_key(
        data=BytesIO(data),
        size=len(data),
        storage_key=storage_key,
        content_type=content_type,
        bucket=bucket,
    )


def get_presigned_url(
    storage_key: str,
    *,
    bucket: str | None = None,
    ttl_seconds: int | None = None,
    filename: str | None = None,
    force_download: bool = False,
    response_content_type: str | None = None,
) -> str:
    """Возвращает presigned URL для скачивания объекта.

    URL подписывается публичным клиентом (``minio_public_endpoint``), поэтому
    сигнатура содержит публичный хост и браузер может открыть файл напрямую.
    Region discovery выполняется один раз через внутренний клиент (``minio_endpoint``),
    чтобы публичный клиент не делал HTTP-запросов к `localhost` изнутри контейнера.

    При ``force_download=True`` добавляет ``response-content-disposition=attachment``
    — браузер скачивает файл вместо открытия inline (снижает риск XSS через HTML-вложения).

    ``response_content_type`` — override ``Content-Type`` ответа (например
    ``text/plain; charset=utf-8`` для корректного отображения UTF-8 в браузере).
    """
    settings = get_settings()
    _bucket = bucket or settings.minio_bucket
    _ttl = ttl_seconds if ttl_seconds is not None else settings.attachment_presign_ttl_seconds
    client = _get_minio_public_client()

    extra_query: dict[str, str | list[str] | tuple[str, ...]] = {}
    if force_download:
        disposition = "attachment"
        if filename:
            # RFC 5987: UTF-8 имя файла через filename*
            from urllib.parse import quote  # noqa: PLC0415

            safe_name = quote(filename, safe="")
            disposition = f"attachment; filename*=UTF-8''{safe_name}"
        extra_query["response-content-disposition"] = disposition
    if response_content_type:
        extra_query["response-content-type"] = response_content_type

    return client.presigned_get_object(
        bucket_name=_bucket,
        object_name=storage_key,
        expires=timedelta(seconds=_ttl),
        extra_query_params=extra_query if extra_query else None,  # type: ignore[arg-type]
    )


def download_object_bytes(storage_key: str, *, bucket: str | None = None) -> bytes:
    """Скачивает объект из MinIO целиком в память. Использовать только для небольших файлов."""
    settings = get_settings()
    _bucket = bucket or settings.minio_bucket
    client = get_minio_client()
    response = client.get_object(bucket_name=_bucket, object_name=storage_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def copy_object_to_new_key(source_key: str, *, bucket: str | None = None) -> str:
    """Копирует объект в том же бакете под новым ключом (для пересылки вложений)."""
    from minio.commonconfig import CopySource

    settings = get_settings()
    _bucket = bucket or settings.minio_bucket
    client = get_minio_client()
    new_key = str(uuid.uuid4())
    client.copy_object(
        bucket_name=_bucket,
        object_name=new_key,
        source=CopySource(_bucket, source_key),
    )
    logger.debug("MinIO: скопирован объект %s → %s", source_key, new_key)
    return new_key


def delete_object(storage_key: str, *, bucket: str | None = None) -> None:
    """Удаляет объект из MinIO. Не бросает исключения, если объект не найден."""
    settings = get_settings()
    _bucket = bucket or settings.minio_bucket
    client = get_minio_client()
    try:
        client.remove_object(bucket_name=_bucket, object_name=storage_key)
        logger.debug("MinIO: удалён объект bucket=%s key=%s", _bucket, storage_key)
    except S3Error as exc:
        if exc.code == "NoSuchKey":
            logger.warning("MinIO: объект не найден при удалении: key=%s", storage_key)
        else:
            logger.error("MinIO: ошибка при удалении key=%s: %s", storage_key, exc)
            raise


_BATCH_DELETE_LIMIT = 1000  # лимит S3 API для delete_objects


def delete_objects(storage_keys: list[str], *, bucket: str | None = None) -> None:
    """Удаляет список объектов батчами по 1000 (лимит S3 API).

    Снижает число HTTP-запросов к MinIO с O(n) до O(n/1000).
    Partial failure (``DeleteError`` в iterator) — ``StorageUnavailableError``,
    чтобы вызывающий не удалял строки БД при оставшихся объектах в бакете.
    """
    if not storage_keys:
        return
    from minio.deleteobjects import DeleteObject

    settings = get_settings()
    _bucket = bucket or settings.minio_bucket
    client = get_minio_client()

    for i in range(0, len(storage_keys), _BATCH_DELETE_LIMIT):
        batch = storage_keys[i : i + _BATCH_DELETE_LIMIT]
        delete_list = [DeleteObject(k) for k in batch]
        errors = list(client.remove_objects(bucket_name=_bucket, delete_object_list=delete_list))
        if errors:
            for err in errors:
                logger.warning(
                    "MinIO batch-delete: ошибка key=%s code=%s message=%s",
                    err.name,
                    err.code,
                    err.message,
                )
            raise StorageUnavailableError()
    logger.debug("MinIO: batch-delete %d объектов bucket=%s", len(storage_keys), _bucket)


async def async_upload_bytes_to_key(
    *,
    data: bytes,
    storage_key: str,
    content_type: str,
    bucket: str | None = None,
) -> str:
    """Async-обёртка над ``upload_bytes_to_key``: выполняет синхронный MinIO SDK в thread pool."""
    return await asyncio.to_thread(
        upload_bytes_to_key,
        data=data,
        storage_key=storage_key,
        content_type=content_type,
        bucket=bucket,
    )


async def async_upload_stream_to_key(
    *,
    data: BinaryIO,
    size: int,
    storage_key: str,
    content_type: str,
    bucket: str | None = None,
) -> str:
    """Async-обёртка над ``upload_stream_to_key``: стрим в MinIO без полного буфера bytes."""
    return await asyncio.to_thread(
        upload_stream_to_key,
        data=data,
        size=size,
        storage_key=storage_key,
        content_type=content_type,
        bucket=bucket,
    )


async def async_delete_objects(storage_keys: list[str], *, bucket: str | None = None) -> None:
    """Async-обёртка над ``delete_objects``: выполняет батч-удаление в thread pool."""
    await asyncio.to_thread(delete_objects, storage_keys, bucket=bucket)


async def async_upload_file(
    *,
    data: BinaryIO,
    size: int,
    content_type: str,
    bucket: str | None = None,
) -> str:
    """Async-обёртка над ``upload_file``: выполняет синхронный MinIO SDK в thread pool.

    Использовать из async-контекста (FastAPI-эндпоинты, сервисы) вместо прямого вызова
    ``upload_file``, чтобы не блокировать event loop.
    """
    return await asyncio.to_thread(upload_file, data=data, size=size, content_type=content_type, bucket=bucket)


async def async_get_presigned_url(
    storage_key: str,
    *,
    bucket: str | None = None,
    ttl_seconds: int | None = None,
    filename: str | None = None,
    force_download: bool = False,
    response_content_type: str | None = None,
) -> str:
    """Async-обёртка над ``get_presigned_url``: выполняет синхронный MinIO SDK в thread pool."""
    return await asyncio.to_thread(
        get_presigned_url,
        storage_key,
        bucket=bucket,
        ttl_seconds=ttl_seconds,
        filename=filename,
        force_download=force_download,
        response_content_type=response_content_type,
    )


async def async_delete_object(storage_key: str, *, bucket: str | None = None) -> None:
    """Async-обёртка над ``delete_object``: выполняет синхронный MinIO SDK в thread pool."""
    await asyncio.to_thread(delete_object, storage_key, bucket=bucket)


async def async_copy_object_to_new_key(source_key: str, *, bucket: str | None = None) -> str:
    """Async-обёртка над ``copy_object_to_new_key``: выполняет синхронный MinIO SDK в thread pool."""
    return await asyncio.to_thread(copy_object_to_new_key, source_key, bucket=bucket)


async def async_download_object_bytes(storage_key: str, *, bucket: str | None = None) -> bytes:
    """Async-обёртка над ``download_object_bytes``: выполняет синхронный MinIO SDK в thread pool."""
    return await asyncio.to_thread(download_object_bytes, storage_key, bucket=bucket)


__all__ = [
    "get_minio_client",
    "ensure_bucket_exists",
    "upload_file",
    "upload_stream_to_key",
    "upload_bytes_to_key",
    "get_presigned_url",
    "download_object_bytes",
    "copy_object_to_new_key",
    "delete_object",
    "delete_objects",
    "async_upload_file",
    "async_upload_bytes_to_key",
    "async_upload_stream_to_key",
    "async_get_presigned_url",
    "async_delete_object",
    "async_delete_objects",
    "async_download_object_bytes",
    "async_copy_object_to_new_key",
]
