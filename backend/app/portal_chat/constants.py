"""Константы домена чатов (лимиты из Settings)."""

from __future__ import annotations

from app.core.config import get_settings


def chat_message_body_max_length() -> int:
    """Единый источник лимита длины сообщения (``Settings.chat_message_body_max_length``)."""
    return get_settings().chat_message_body_max_length


# Для аннотаций Pydantic Field (дефолт совпадает с Settings)
CHAT_MESSAGE_BODY_MAX_LENGTH = 32_000

# Максимум одновременно закреплённых сообщений в одном чате (защита от захламления UI).
CHAT_PINNED_MESSAGES_MAX_PER_CHAT = 50

# Длина фрагмента «ответить с цитатой».
CHAT_REPLY_QUOTE_TEXT_MAX_LENGTH = 1000

# Число столбцов waveform голосового сообщения (контракт с клиентом).
VOICE_WAVEFORM_BARS = 28
