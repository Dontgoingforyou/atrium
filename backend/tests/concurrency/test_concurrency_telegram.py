"""Гонка привязки Telegram: UNIQUE chat_id / PK user_sub."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest
from app.infrastructure.db.models.portal_telegram_binding import PortalTelegramBinding
from app.portal_telegram.services.binding import confirm_bind
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


@pytest.mark.asyncio
async def test_parallel_confirm_bind_same_user_one_row(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    codes = ["tgb_code_a", "tgb_code_b"]
    redis = AsyncMock()
    redis.getdel = AsyncMock(side_effect=["user-tg", "user-tg"])
    redis.delete = AsyncMock()

    async def try_bind(code: str) -> None:
        async with sqlite_concurrency_factory() as sess:
            await confirm_bind(sess, redis, code, telegram_chat_id=42_001)

    await asyncio.gather(try_bind(codes[0]), try_bind(codes[1]))

    async with sqlite_concurrency_factory() as s:
        n = await s.execute(select(func.count()).select_from(PortalTelegramBinding))
        assert n.scalar_one() == 1
        row = await s.scalar(select(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == "user-tg"))
        assert row is not None
        assert row.telegram_chat_id == 42_001


@pytest.mark.asyncio
async def test_parallel_confirm_bind_two_users_one_chat_id(
    sqlite_concurrency_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Гонка: два user_sub, один telegram_chat_id — одна строка, steal semantics."""
    chat_id = 88_888
    redis = AsyncMock()
    redis.getdel = AsyncMock(side_effect=["user-a", "user-b"])
    redis.delete = AsyncMock()

    async def try_bind(user_sub: str, code: str) -> None:
        async with sqlite_concurrency_factory() as sess:
            await confirm_bind(sess, redis, code, telegram_chat_id=chat_id)

    await asyncio.gather(
        try_bind("user-a", "tgb_code_a"),
        try_bind("user-b", "tgb_code_b"),
        return_exceptions=True,
    )

    async with sqlite_concurrency_factory() as s:
        n = await s.execute(select(func.count()).select_from(PortalTelegramBinding))
        assert n.scalar_one() == 1
        rows = (await s.execute(select(PortalTelegramBinding))).scalars().all()
        assert len(rows) == 1
        assert rows[0].telegram_chat_id == chat_id
        assert rows[0].user_sub in {"user-a", "user-b"}
