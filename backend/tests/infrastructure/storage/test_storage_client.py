"""Модульные тесты MinIO-клиента (`app.infrastructure.storage.client`)."""

from __future__ import annotations

import uuid
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.parse import quote

import pytest
from app.core.config import Settings
from app.core.exceptions import StorageUnavailableError
from minio.commonconfig import CopySource
from minio.deleteobjects import DeleteError
from minio.error import S3Error


def _minio_settings(**kwargs: object) -> Settings:
    base: dict[str, object] = {
        "database_url": "sqlite:///:memory:",
        "minio_bucket": "test-bucket",
        "minio_endpoint": "internal:9000",
        "minio_public_endpoint": "public.host:443",
        "minio_access_key": "ak",
        "minio_secret_key": "sk",
        "attachment_presign_ttl_seconds": 3600,
    }
    base.update(kwargs)
    return Settings(**base)


def _clear_storage_caches() -> None:
    from app.infrastructure.storage import client as storage_client

    storage_client.get_minio_client.cache_clear()
    storage_client._get_minio_public_client.cache_clear()


def test_get_minio_client_singleton_uses_settings() -> None:
    _clear_storage_caches()
    settings = _minio_settings(
        minio_endpoint="in:9000",
        minio_access_key="a",
        minio_secret_key="b",
        minio_internal_secure=True,
    )
    inst = MagicMock()

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=settings),
        patch("app.infrastructure.storage.client.Minio", return_value=inst) as minio_cls,
    ):
        from app.infrastructure.storage import client as storage_client

        first = storage_client.get_minio_client()
        second = storage_client.get_minio_client()

    assert first is inst is second
    minio_cls.assert_called_once()
    assert minio_cls.call_args.kwargs == {
        "endpoint": "in:9000",
        "access_key": "a",
        "secret_key": "b",
        "secure": True,
    }


def _s3_error(*, code: str | None = "InternalError") -> S3Error:
    return S3Error(
        response=MagicMock(),
        code=code,
        message="msg",
        resource="/",
        request_id="rid",
        host_id="hid",
    )


def test_get_presigned_url_uses_trimmed_public_endpoint_and_region() -> None:
    _clear_storage_caches()
    settings = _minio_settings(
        minio_public_endpoint="  pub.example:9443  ",
        minio_endpoint="internal.local:9000",
    )
    inner_client = MagicMock()
    inner_client._get_region.return_value = "eu-test"
    public_instance = MagicMock()
    public_instance.presigned_get_object.return_value = "https://signed.example/obj"

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=settings),
        patch("app.infrastructure.storage.client.get_minio_client", return_value=inner_client),
        patch("app.infrastructure.storage.client.Minio", return_value=public_instance) as minio_cls,
    ):
        from app.infrastructure.storage.client import get_presigned_url

        url = get_presigned_url("key-1", ttl_seconds=120)

    assert url == "https://signed.example/obj"
    inner_client._get_region.assert_called_once_with("test-bucket")
    kwargs = minio_cls.call_args.kwargs
    assert kwargs["endpoint"] == "pub.example:9443"
    assert kwargs["region"] == "eu-test"
    assert kwargs["access_key"] == "ak"
    assert kwargs["secret_key"] == "sk"
    assert public_instance.presigned_get_object.call_args.kwargs["expires"].total_seconds() == 120


def test_get_presigned_url_falls_back_to_internal_endpoint() -> None:
    _clear_storage_caches()
    settings = _minio_settings(
        minio_public_endpoint="   ",
        minio_endpoint="only-internal:9000",
    )
    inner_client = MagicMock()
    inner_client._get_region.return_value = "r1"
    public_instance = MagicMock()
    public_instance.presigned_get_object.return_value = "https://internal/obj"

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=settings),
        patch("app.infrastructure.storage.client.get_minio_client", return_value=inner_client),
        patch("app.infrastructure.storage.client.Minio", return_value=public_instance) as minio_cls,
    ):
        from app.infrastructure.storage.client import get_presigned_url

        get_presigned_url("key-1")

    assert minio_cls.call_args.kwargs["endpoint"] == "only-internal:9000"


def test_ensure_bucket_exists_creates_when_missing() -> None:
    client = MagicMock()
    client.bucket_exists.return_value = False

    with (
        patch("app.infrastructure.storage.client.get_minio_client", return_value=client),
        patch("app.infrastructure.storage.client.logger") as log,
    ):
        from app.infrastructure.storage.client import ensure_bucket_exists

        ensure_bucket_exists("my-bucket")

    client.bucket_exists.assert_called_once_with("my-bucket")
    client.make_bucket.assert_called_once_with("my-bucket")
    log.info.assert_called()


def test_ensure_bucket_exists_skips_make_when_present() -> None:
    client = MagicMock()
    client.bucket_exists.return_value = True

    with patch("app.infrastructure.storage.client.get_minio_client", return_value=client):
        from app.infrastructure.storage.client import ensure_bucket_exists

        ensure_bucket_exists("my-bucket")

    client.make_bucket.assert_not_called()


def test_ensure_bucket_exists_raises_on_s3_error() -> None:
    client = MagicMock()
    client.bucket_exists.side_effect = _s3_error(code="NoSuchBucket")

    with (
        patch("app.infrastructure.storage.client.get_minio_client", return_value=client),
        patch("app.infrastructure.storage.client.logger") as log,
    ):
        from app.infrastructure.storage.client import ensure_bucket_exists

        with pytest.raises(S3Error):
            ensure_bucket_exists("x")

    log.error.assert_called()


def test_upload_file_puts_object_and_returns_key() -> None:
    fixed = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    client = MagicMock()
    data = BytesIO(b"hello")

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch("app.infrastructure.storage.client.get_minio_client", return_value=client),
        patch("app.infrastructure.storage.client.uuid.uuid4", return_value=fixed),
        patch("app.infrastructure.storage.client.logger"),
    ):
        from app.infrastructure.storage.client import upload_file

        key = upload_file(data=data, size=5, content_type="text/plain", bucket="other")

    assert key == str(fixed)
    client.put_object.assert_called_once()
    call_kw = client.put_object.call_args.kwargs
    assert call_kw["bucket_name"] == "other"
    assert call_kw["object_name"] == str(fixed)
    assert call_kw["length"] == 5
    assert call_kw["content_type"] == "text/plain"


def test_upload_stream_to_key() -> None:
    client = MagicMock()
    stream = BytesIO(b"abc")

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch("app.infrastructure.storage.client.get_minio_client", return_value=client),
        patch("app.infrastructure.storage.client.logger"),
    ):
        from app.infrastructure.storage.client import upload_stream_to_key

        key = upload_stream_to_key(
            data=stream,
            size=3,
            storage_key="rich-media/x/a.png",
            content_type="image/png",
        )

    assert key == "rich-media/x/a.png"
    kw = client.put_object.call_args.kwargs
    assert kw["object_name"] == "rich-media/x/a.png"
    assert kw["data"] is stream
    assert kw["length"] == 3


def test_upload_bytes_to_key() -> None:
    client = MagicMock()

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch("app.infrastructure.storage.client.get_minio_client", return_value=client),
        patch("app.infrastructure.storage.client.logger"),
    ):
        from app.infrastructure.storage.client import upload_bytes_to_key

        upload_bytes_to_key(
            data=b"abc",
            storage_key="avatars/u/x.jpg",
            content_type="image/jpeg",
        )

    client.put_object.assert_called_once()
    kw = client.put_object.call_args.kwargs
    assert kw["bucket_name"] == "test-bucket"
    assert kw["object_name"] == "avatars/u/x.jpg"
    bio = kw["data"]
    assert isinstance(bio, BytesIO)
    assert bio.read() == b"abc"


def test_get_presigned_url_uses_public_client_and_ttl() -> None:
    pub = MagicMock()
    pub.presigned_get_object.return_value = "https://signed.example/obj"

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch(
            "app.infrastructure.storage.client._get_minio_public_client",
            return_value=pub,
        ),
    ):
        from app.infrastructure.storage.client import get_presigned_url

        url = get_presigned_url("key-1", ttl_seconds=120)

    assert url == "https://signed.example/obj"
    pub.presigned_get_object.assert_called_once()
    assert pub.presigned_get_object.call_args.kwargs["bucket_name"] == "test-bucket"
    assert pub.presigned_get_object.call_args.kwargs["object_name"] == "key-1"
    td = pub.presigned_get_object.call_args.kwargs["expires"]
    assert td.total_seconds() == 120


def test_get_presigned_url_default_ttl_from_settings() -> None:
    pub = MagicMock()
    pub.presigned_get_object.return_value = "https://signed.example/obj"
    settings = _minio_settings(attachment_presign_ttl_seconds=1800)

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=settings),
        patch(
            "app.infrastructure.storage.client._get_minio_public_client",
            return_value=pub,
        ),
    ):
        from app.infrastructure.storage.client import get_presigned_url

        get_presigned_url("key-1")

    assert pub.presigned_get_object.call_args.kwargs["expires"].total_seconds() == 1800


def test_get_presigned_url_force_download_filename_utf8() -> None:
    pub = MagicMock()
    pub.presigned_get_object.return_value = "https://signed.example/obj"
    filename = 'отчёт "<script>.html'

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch(
            "app.infrastructure.storage.client._get_minio_public_client",
            return_value=pub,
        ),
    ):
        from app.infrastructure.storage.client import get_presigned_url

        get_presigned_url("key-1", force_download=True, filename=filename)

    extra = pub.presigned_get_object.call_args.kwargs["extra_query_params"]
    disposition = extra["response-content-disposition"]
    assert disposition.startswith("attachment; filename*=UTF-8''")
    assert "<script>" not in disposition
    assert quote(filename, safe="") in disposition


def test_get_presigned_url_response_content_type_charset() -> None:
    pub = MagicMock()
    pub.presigned_get_object.return_value = "https://signed.example/obj"

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch(
            "app.infrastructure.storage.client._get_minio_public_client",
            return_value=pub,
        ),
    ):
        from app.infrastructure.storage.client import get_presigned_url

        get_presigned_url("key-md", response_content_type="text/markdown; charset=utf-8")

    extra = pub.presigned_get_object.call_args.kwargs["extra_query_params"]
    assert extra["response-content-type"] == "text/markdown; charset=utf-8"


def test_download_object_bytes_reads_and_closes_response() -> None:
    client = MagicMock()
    response = MagicMock()
    response.read.return_value = b"payload"
    client.get_object.return_value = response

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch("app.infrastructure.storage.client.get_minio_client", return_value=client),
    ):
        from app.infrastructure.storage.client import download_object_bytes

        assert download_object_bytes("obj-1") == b"payload"

    client.get_object.assert_called_once_with(bucket_name="test-bucket", object_name="obj-1")
    response.close.assert_called_once()
    response.release_conn.assert_called_once()


def test_copy_object_to_new_key() -> None:
    fixed = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
    client = MagicMock()

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch("app.infrastructure.storage.client.get_minio_client", return_value=client),
        patch("app.infrastructure.storage.client.uuid.uuid4", return_value=fixed),
        patch("app.infrastructure.storage.client.logger"),
    ):
        from app.infrastructure.storage.client import copy_object_to_new_key

        new_key = copy_object_to_new_key("src-key")

    assert new_key == str(fixed)
    client.copy_object.assert_called_once()
    kw = client.copy_object.call_args.kwargs
    assert kw["bucket_name"] == "test-bucket"
    assert kw["object_name"] == str(fixed)
    assert kw["source"] == CopySource("test-bucket", "src-key")


def test_delete_object_success_and_no_such_key_swallowed() -> None:
    client = MagicMock()
    err_no_key = _s3_error(code="NoSuchKey")
    err_other = _s3_error(code="AccessDenied")

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch("app.infrastructure.storage.client.get_minio_client", return_value=client),
        patch("app.infrastructure.storage.client.logger") as log,
    ):
        from app.infrastructure.storage.client import delete_object

        delete_object("k1")
        client.remove_object.side_effect = err_no_key
        delete_object("missing")
        client.remove_object.side_effect = err_other

        with pytest.raises(S3Error):
            delete_object("bad")

    assert client.remove_object.call_count == 3
    log.warning.assert_called()


def test_delete_objects_empty_noop() -> None:
    client = MagicMock()

    with patch("app.infrastructure.storage.client.get_minio_client", return_value=client):
        from app.infrastructure.storage.client import delete_objects

        delete_objects([])

    client.remove_objects.assert_not_called()


def test_delete_objects_batches_on_success() -> None:
    client = MagicMock()
    client.remove_objects.return_value = iter(())

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch("app.infrastructure.storage.client.get_minio_client", return_value=client),
        patch("app.infrastructure.storage.client._BATCH_DELETE_LIMIT", 2),
        patch("app.infrastructure.storage.client.logger") as log,
    ):
        from app.infrastructure.storage.client import delete_objects

        delete_objects(["a", "b", "c", "d"])

    assert client.remove_objects.call_count == 2
    log.debug.assert_called()
    log.warning.assert_not_called()


def test_delete_objects_partial_failure_raises() -> None:
    """DeleteError в батче — стоп, иначе purge сотрёт строки БД при живых объектах."""
    client = MagicMock()
    client.remove_objects.return_value = iter([DeleteError("SlowDown", "rate limit", "k-bad", None)])

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch("app.infrastructure.storage.client.get_minio_client", return_value=client),
        patch("app.infrastructure.storage.client._BATCH_DELETE_LIMIT", 2),
        patch("app.infrastructure.storage.client.logger") as log,
    ):
        from app.infrastructure.storage.client import delete_objects

        with pytest.raises(StorageUnavailableError):
            delete_objects(["a", "b", "c", "d"])

    assert client.remove_objects.call_count == 1
    log.warning.assert_called()
    log.debug.assert_not_called()


def test_delete_objects_second_batch_failure_after_first_success() -> None:
    client = MagicMock()
    client.remove_objects.side_effect = [
        iter(()),
        iter([DeleteError("SlowDown", "rate limit", "c", None)]),
    ]

    with (
        patch("app.infrastructure.storage.client.get_settings", return_value=_minio_settings()),
        patch("app.infrastructure.storage.client.get_minio_client", return_value=client),
        patch("app.infrastructure.storage.client._BATCH_DELETE_LIMIT", 2),
    ):
        from app.infrastructure.storage.client import delete_objects

        with pytest.raises(StorageUnavailableError):
            delete_objects(["a", "b", "c", "d"])

    assert client.remove_objects.call_count == 2
