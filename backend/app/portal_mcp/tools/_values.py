"""Разбор аргументов тулов в типы доменных схем."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from app.core.exceptions import ValidationError


def parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise ValidationError("Некорректный идентификатор") from exc


def parse_uuids(values: list[str] | None) -> list[uuid.UUID] | None:
    if values is None:
        return None
    return [parse_uuid(item) for item in values]


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("Дата ожидается в формате ГГГГ-ММ-ДД") from exc


def parse_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("Дата и время ожидаются в формате ISO 8601") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed
