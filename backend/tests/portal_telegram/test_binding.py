"""Юнит-тесты привязки Telegram."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.infrastructure.db.models.portal_telegram_binding import PortalTelegramBinding
from app.portal_telegram.services.binding import (
    BindCodeInvalidError,
    confirm_bind,
    delete_binding_for_user,
    generate_bind_code,
    get_binding,
    get_binding_by_chat_id,
    unlink,
    unlink_by_chat_id,
)
from sqlalchemy import select


@pytest.mark.asyncio
async def test_generate_bind_code_stores_in_redis() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    code = await generate_bind_code(redis, "user-sub")
    assert code.startswith("tgb_")
    assert redis.set.await_count == 2
    first_key = redis.set.await_args_list[0][0][0]
    assert first_key.startswith("tg_bind:")
    second_key = redis.set.await_args_list[1][0][0]
    assert second_key.startswith("tg_bind_user:")


@pytest.mark.asyncio
async def test_generate_bind_code_invalidates_previous() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value="tgb_oldcode")
    redis.delete = AsyncMock()
    redis.set = AsyncMock()
    await generate_bind_code(redis, "user-sub")
    redis.delete.assert_awaited()
    deleted_key = redis.delete.await_args[0][0]
    assert deleted_key == "tg_bind:tgb_oldcode"


@pytest.mark.asyncio
async def test_confirm_bind_inserts_row(sqlite_session) -> None:
    redis = AsyncMock()
    redis.getdel = AsyncMock(return_value="user-sub")
    redis.delete = AsyncMock()
    code = "tgb_testcode123"
    await confirm_bind(sqlite_session, redis, code, 999888777)
    redis.getdel.assert_awaited_once()
    row = await sqlite_session.scalar(select(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == "user-sub"))
    assert row is not None
    assert row.telegram_chat_id == 999888777


@pytest.mark.asyncio
async def test_confirm_bind_invalid_code(sqlite_session) -> None:
    redis = AsyncMock()
    redis.getdel = AsyncMock(return_value=None)
    with pytest.raises(BindCodeInvalidError):
        await confirm_bind(sqlite_session, redis, "tgb_bad", 1)


@pytest.mark.asyncio
async def test_delete_binding_for_user_does_not_commit(sqlite_session) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=42))
    await sqlite_session.commit()
    await delete_binding_for_user(sqlite_session, "user-sub")
    await sqlite_session.rollback()
    row = await sqlite_session.scalar(select(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == "user-sub"))
    assert row is not None


@pytest.mark.asyncio
async def test_unlink_removes_row(sqlite_session) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=42))
    await sqlite_session.commit()
    await unlink(sqlite_session, "user-sub")
    row = await sqlite_session.scalar(select(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == "user-sub"))
    assert row is None


@pytest.mark.asyncio
async def test_get_binding_returns_model(sqlite_session) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=1))
    await sqlite_session.commit()
    row = await get_binding(sqlite_session, "user-sub")
    assert row is not None
    assert row.telegram_chat_id == 1


@pytest.mark.asyncio
async def test_confirm_bind_empty_code_raises(sqlite_session) -> None:
    redis = AsyncMock()
    with pytest.raises(BindCodeInvalidError, match="empty_code"):
        await confirm_bind(sqlite_session, redis, "  ", 1)
    redis.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_confirm_bind_updates_existing_chat_id(sqlite_session) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=111))
    await sqlite_session.commit()
    redis = AsyncMock()
    redis.getdel = AsyncMock(return_value="user-sub")
    redis.delete = AsyncMock()
    await confirm_bind(sqlite_session, redis, "tgb_x", 222)
    row = await sqlite_session.scalar(select(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == "user-sub"))
    assert row is not None
    assert row.telegram_chat_id == 222


@pytest.mark.asyncio
async def test_unlink_by_chat_id_removes_row(sqlite_session) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=999))
    await sqlite_session.commit()
    await unlink_by_chat_id(sqlite_session, 999)
    row = await sqlite_session.scalar(
        select(PortalTelegramBinding).where(PortalTelegramBinding.telegram_chat_id == 999)
    )
    assert row is None


@pytest.mark.asyncio
async def test_confirm_bind_steals_chat_id_from_other_user(sqlite_session) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="other-sub", telegram_chat_id=4242))
    await sqlite_session.commit()
    redis = AsyncMock()
    redis.getdel = AsyncMock(return_value="user-sub")
    redis.delete = AsyncMock()
    await confirm_bind(sqlite_session, redis, "tgb_steal", 4242)
    stolen = await sqlite_session.scalar(
        select(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == "other-sub")
    )
    assert stolen is None
    mine = await sqlite_session.scalar(
        select(PortalTelegramBinding).where(PortalTelegramBinding.user_sub == "user-sub")
    )
    assert mine is not None
    assert mine.telegram_chat_id == 4242


@pytest.mark.asyncio
async def test_get_binding_by_chat_id_returns_row(sqlite_session) -> None:
    sqlite_session.add(PortalTelegramBinding(user_sub="user-sub", telegram_chat_id=555))
    await sqlite_session.commit()
    row = await get_binding_by_chat_id(sqlite_session, 555)
    assert row is not None
    assert row.user_sub == "user-sub"
