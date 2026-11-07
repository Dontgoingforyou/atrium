"""Разбор файла из аргумента тула MCP (base64 в JSON-RPC)."""

from __future__ import annotations

import base64
import binascii
import io

from app.core.exceptions import ValidationError
from app.portal_mcp.constants import MCP_FILE_MAX_BYTES

MAX_ENCODED_LENGTH = (MCP_FILE_MAX_BYTES + 2) // 3 * 4 + 4


def decode_mcp_file(content_base64: str) -> tuple[io.BytesIO, int]:
    """Декодирует base64 и отсекает пустой или слишком большой файл до сервиса."""
    stripped = "".join(content_base64.split())
    if not stripped:
        raise ValidationError("Файл пустой")
    if len(stripped) > MAX_ENCODED_LENGTH:
        raise ValidationError(_too_large_message())
    try:
        raw = base64.b64decode(stripped, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationError("Некорректный base64 файла") from exc
    size = len(raw)
    if size <= 0:
        raise ValidationError("Файл пустой")
    if size > MCP_FILE_MAX_BYTES:
        raise ValidationError(_too_large_message())
    return io.BytesIO(raw), size


def _too_large_message() -> str:
    max_mib = MCP_FILE_MAX_BYTES // (1024 * 1024)
    return f"Через MCP можно передать файл не больше {max_mib} МиБ"
