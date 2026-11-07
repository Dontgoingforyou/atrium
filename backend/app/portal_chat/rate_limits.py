"""Rate limit для мутаций чата (защита от storage/message DoS при компрометации токена)."""

from __future__ import annotations

import uuid

from app.core.config import get_settings
from app.infrastructure.cache.rate_limit import enforce_rate_limit


async def enforce_chat_attachment_upload_limit(user_sub: str) -> None:
    """Лимит загрузок вложений на пользователя (скользящее окно)."""
    s = get_settings()
    await enforce_rate_limit(
        f"rl:chat-attach:{user_sub}",
        limit=s.chat_attachment_upload_rate_limit,
        window_seconds=s.chat_attachment_upload_rate_window_seconds,
        message="Слишком много загрузок файлов. Подождите и повторите.",
    )


async def enforce_chat_transcribe_limit(user_sub: str) -> None:
    """Лимит запросов транскрибации на пользователя (скользящее окно)."""
    s = get_settings()
    await enforce_rate_limit(
        f"rl:chat-transcribe:{user_sub}",
        limit=s.chat_whisper_rate_limit,
        window_seconds=s.chat_whisper_rate_window_seconds,
        message="Слишком много запросов транскрибации. Подождите и повторите.",
    )


async def enforce_chat_message_post_limit(user_sub: str, chat_id: uuid.UUID) -> None:
    """Лимит отправки сообщений: per-user и per-chat."""
    s = get_settings()
    await enforce_rate_limit(
        f"rl:chat-msg:user:{user_sub}",
        limit=s.chat_message_post_rate_limit_per_user,
        window_seconds=s.chat_message_post_rate_window_seconds,
        message="Слишком много сообщений. Подождите и повторите.",
    )
    await enforce_rate_limit(
        f"rl:chat-msg:chat:{chat_id}:{user_sub}",
        limit=s.chat_message_post_rate_limit_per_chat,
        window_seconds=s.chat_message_post_rate_window_seconds,
        message="Слишком много сообщений в этом чате. Подождите и повторите.",
    )
