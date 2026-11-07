from __future__ import annotations

import base64
import hmac
import json
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


def hmac_secrets_equal(got: str | None, expected: str) -> bool:
    """Сравнить секреты через ``hmac.compare_digest`` без ``ValueError`` на разной длине.

    CPython поднимает ``ValueError``, если строки разной длины — это даёт 500 вместо 403.
    Пустые значения — отказ (fail-closed).
    """
    if not got or not expected or len(got) != len(expected):
        return False
    return hmac.compare_digest(got, expected)


def now_utc() -> datetime:
    """Текущее время в UTC. Используется как единая точка получения временной метки."""
    return datetime.now(UTC)


def decode_jwt_payload_unverified(token: str) -> dict[str, Any] | None:
    """Декодировать payload JWT без верификации подписи.

    Возвращает словарь claims или ``None`` при любой ошибке декодирования.
    Предназначена исключительно для вспомогательных задач:
    - вычисление TTL Redis-кэша по полю ``exp`` (``deps_auth``);
    - выбор режима photo-proxy (``portal_users``) по полю ``sub``.
    **Не использовать для проверки авторизации — подпись не верифицируется.**
    """
    try:
        parts = token.split(".")
        if len(parts) < 2:  # noqa: PLR2004
            return None
        raw = base64.urlsafe_b64decode(parts[1] + "==").decode("utf-8")
        return dict(json.loads(raw))
    except Exception as exc:
        logger.debug("decode_jwt_payload_unverified: не удалось декодировать payload: %s", exc)
        return None
