"""Unit-тесты ``file_upload_validation.check_magic_bytes`` и потока загрузки."""

from __future__ import annotations

from io import BytesIO

import pytest
from app.core.exceptions import ValidationError
from app.services.file_upload_validation import check_magic_bytes, open_upload_stream
from fastapi import UploadFile


def test_check_magic_bytes_accepts_png_header() -> None:
    header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    assert check_magic_bytes(header, "image/png", reject_unknown=True)


def test_check_magic_bytes_rejects_png_claimed_as_jpeg() -> None:
    header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    assert not check_magic_bytes(header, "image/jpeg", reject_unknown=True)


def test_check_magic_bytes_accepts_jpeg_header() -> None:
    header = b"\xff\xd8\xff\xe0" + b"\x00" * 8
    assert check_magic_bytes(header, "image/jpeg", reject_unknown=True)


async def test_open_upload_stream_known_size_reuses_file_without_copy() -> None:
    raw = BytesIO(b"hello")
    upload = UploadFile(filename="a.bin", file=raw, size=5)
    async with open_upload_stream(upload, 100) as (stream, size):
        assert stream is raw
        assert size == 5
        assert stream.read() == b"hello"


async def test_open_upload_stream_rejects_declared_size_before_read() -> None:
    raw = BytesIO(b"hello")
    upload = UploadFile(filename="a.bin", file=raw, size=50)
    with pytest.raises(ValidationError, match="Размер файла"):
        async with open_upload_stream(upload, 10):
            pass
    assert raw.tell() == 0


async def test_open_upload_stream_unknown_size_reads_chunks() -> None:
    payload = b"abc" * 30
    raw = BytesIO(payload)
    upload = UploadFile(filename="a.bin", file=raw)
    async with open_upload_stream(upload, 1000) as (stream, size):
        assert size == len(payload)
        assert stream is not raw
        assert stream.read() == payload


async def test_open_upload_stream_unknown_size_over_limit() -> None:
    upload = UploadFile(filename="a.bin", file=BytesIO(b"abcdef"))
    with pytest.raises(ValidationError, match="Размер файла"):
        async with open_upload_stream(upload, 3):
            pass
