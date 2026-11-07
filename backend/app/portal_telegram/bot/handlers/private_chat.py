"""Команды бота — только личный чат (не группа/канал)."""

from __future__ import annotations

from aiogram.enums import ChatType
from aiogram.types import Message

_PRIVATE_ONLY_REPLY = "Команды бота работают только в личном чате с ботом."


async def ensure_private_chat(message: Message) -> bool:
    """True, если личный чат; иначе отвечает отказом и False."""
    if message.chat.type == ChatType.PRIVATE:
        return True
    await message.answer(_PRIVATE_ONLY_REPLY)
    return False
