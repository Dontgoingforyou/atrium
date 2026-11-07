from __future__ import annotations

import logging
import uuid

import redis.asyncio as aioredis
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.portal_telegram_binding import PortalTelegramBinding
from app.portal_telegram.constants import (
    TG_BIND_CODE_TTL_SECONDS,
    TG_BIND_REDIS_PREFIX,
    TG_BIND_USER_REDIS_PREFIX,
)

logger = logging.getLogger(__name__)


def _bind_key(code: str) -> str:
    return f"{TG_BIND_REDIS_PREFIX}{code}"


def _user_bind_key(user_sub: str) -> str:
    return f"{TG_BIND_USER_REDIS_PREFIX}{user_sub}"


def generate_bind_code_value() -> str:
    return f"tgb_{uuid.uuid4().hex}"


async def generate_bind_code(redis: aioredis.Redis, user_sub: str) -> str:
    user_key = _user_bind_key(user_sub)
    old_code = await redis.get(user_key)
    if old_code is not None:
        await redis.delete(_bind_key(str(old_code)))
    code = generate_bind_code_value()
    await redis.set(_bind_key(code), user_sub, ex=TG_BIND_CODE_TTL_SECONDS)
    await redis.set(user_key, code, ex=TG_BIND_CODE_TTL_SECONDS)
    return code


class BindCodeInvalidError(Exception):
    pass


async def confirm_bind(
    db: AsyncSession,
    redis: aioredis.Redis,
    code: str,
    telegram_chat_id: int,
) -> None:
    if not code.strip():
        raise BindCodeInvalidError("empty_code")
    key = _bind_key(code.strip())
    user_sub_raw = await redis.getdel(key)
    if user_sub_raw is None:
        raise BindCodeInvalidError("expired_or_unknown")
    user_sub = str(user_sub_raw)
    await redis.delete(_user_bind_key(user_sub))

    async def _upsert() -> None:
        other = await db.scalar(
            select(PortalTelegramBinding).where(
                PortalTelegramBinding.telegram_chat_id == telegram_chat_id,
                PortalTelegramBinding.user_sub != user_sub,
            )
        )
        if other is not None:
            await db.delete(other)

        row = await db.scalar(select(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == user_sub))
        if row is None:
            db.add(PortalTelegramBinding(user_sub=user_sub, telegram_chat_id=telegram_chat_id))
        else:
            row.telegram_chat_id = telegram_chat_id
        await db.commit()

    try:
        await _upsert()
    except IntegrityError:
        await db.rollback()
        await _upsert()
    logger.info("Telegram привязан: user_sub prefix=%s…", user_sub[:20])


async def delete_binding_for_user(db: AsyncSession, user_sub: str) -> None:
    """Снять привязку без commit (для чужой транзакции, например purge специалиста)."""
    await db.execute(delete(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == user_sub))


async def unlink(db: AsyncSession, user_sub: str) -> None:
    await delete_binding_for_user(db, user_sub)
    await db.commit()


async def unlink_by_chat_id(db: AsyncSession, telegram_chat_id: int) -> None:
    await db.execute(delete(PortalTelegramBinding).where(PortalTelegramBinding.telegram_chat_id == telegram_chat_id))
    await db.commit()


async def get_binding(db: AsyncSession, user_sub: str) -> PortalTelegramBinding | None:
    row = await db.scalar(select(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == user_sub))
    return row


async def get_binding_by_chat_id(db: AsyncSession, telegram_chat_id: int) -> PortalTelegramBinding | None:
    row = await db.scalar(
        select(PortalTelegramBinding).where(PortalTelegramBinding.telegram_chat_id == telegram_chat_id)
    )
    return row
