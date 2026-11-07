from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.infrastructure.db.session import async_session_factory
from app.portal_telegram.bot.handlers.private_chat import ensure_private_chat
from app.portal_telegram.services.binding import get_binding_by_chat_id, unlink_by_chat_id

router = Router(name="tg_common")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if not await ensure_private_chat(message):
        return
    await message.answer(
        "Команды:\n"
        "/start КОД — привязать портал (код выдаётся на сайте)\n"
        "/status — проверить привязку\n"
        "/unlink — отвязать этот чат от портала\n"
        "/help — эта справка"
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    if not await ensure_private_chat(message):
        return
    async with async_session_factory() as db:
        row = await get_binding_by_chat_id(db, int(message.chat.id))
    if row is None:
        await message.answer("Чат не привязан к порталу. Получите код на сайте и выполните /start с кодом.")
        return
    await message.answer("Чат привязан к учётной записи портала. Уведомления дублируются сюда.")


@router.message(Command("unlink"))
async def cmd_unlink(message: Message) -> None:
    if not await ensure_private_chat(message):
        return
    async with async_session_factory() as db:
        row = await get_binding_by_chat_id(db, int(message.chat.id))
        if row is None:
            await message.answer("Привязки не было.")
            return
        await unlink_by_chat_id(db, int(message.chat.id))
    await message.answer("Привязка снята. Вы можете снова подключить бот с сайта.")
