from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.infrastructure.cache.token_cache import get_redis_client
from app.infrastructure.db.session import async_session_factory
from app.portal_telegram.bot.handlers.private_chat import ensure_private_chat
from app.portal_telegram.services.binding import BindCodeInvalidError, confirm_bind

logger = logging.getLogger(__name__)

router = Router(name="tg_start")


@router.message(Command("start"))
async def cmd_start(message: Message, command: CommandObject) -> None:
    if not await ensure_private_chat(message):
        return
    code = (command.args or "").strip()
    if not code:
        await message.answer(
            "Привет. Чтобы привязать аккаунт портала, откройте ссылку с сайта "
            "(Настройки → Подключить Telegram) и нажмите «Открыть бот»."
        )
        return
    redis = get_redis_client()
    if redis is None:
        await message.answer("Привязка временно недоступна (нет Redis). Попробуйте позже.")
        return
    chat_id = message.chat.id
    async with async_session_factory() as db:
        try:
            await confirm_bind(db, redis, code, int(chat_id))
        except BindCodeInvalidError:
            await message.answer("Код недействителен или истёк. Запросите новый код на портале.")
            return
        except Exception:
            logger.exception("Ошибка привязки Telegram")
            await message.answer("Не удалось привязать аккаунт. Попробуйте позже.")
            return
    await message.answer("✅ Аккаунт привязан. Уведомления будут приходить сюда.")
