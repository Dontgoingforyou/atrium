"""Общий конструктор ``AsyncOpenAI``-клиента.

Используется доменами, которым нужен прямой вызов OpenAI API (генерация эмбеддингов —
``portal_search``, транскрибация голосовых сообщений — ``portal_chat``). Проверка наличия
``api_key`` и тип поднимаемой ошибки при его отсутствии — на стороне вызывающего домена
(разные типы: ``RuntimeError`` для поиска, ``ServiceUnavailableError`` для чата), здесь —
только сборка клиента.
"""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from app.core.config import get_settings


def build_openai_client(*, api_key: str, base_url: str = "", timeout: float | None = None) -> AsyncOpenAI:
    """Создаёт ``AsyncOpenAI``-клиент по переданным ``api_key``/``base_url``.

    Таймаут — ``timeout`` или ``Settings.http_client_timeout_seconds``.
    """
    kwargs: dict[str, Any] = {
        "api_key": api_key,
        "timeout": timeout if timeout is not None else get_settings().http_client_timeout_seconds,
    }
    if base_url:
        kwargs["base_url"] = base_url
    return AsyncOpenAI(**kwargs)
