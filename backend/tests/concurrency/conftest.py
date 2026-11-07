"""Общая file-SQLite фикстура для гонок: две сессии, WAL, FK."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import app.infrastructure.db.models  # noqa: F401 — metadata
import pytest
from app.infrastructure.db.base import Base
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.schemas.auth import UserPublic
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest.fixture
async def sqlite_concurrency_factory(tmp_path: Path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    db_file = tmp_path / "concurrency.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_connection: object, _connection_record: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    yield factory
    await engine.dispose()


def profile_from_user(
    user: UserPublic,
    *,
    portal_chat_allowed: bool = True,
    is_developer: bool = False,
) -> PortalUserProfile:
    return PortalUserProfile(
        sub=user.sub,
        email=user.email,
        full_name=user.full_name,
        username=user.username,
        is_portal_admin=user.is_portal_admin,
        is_developer=is_developer,
        portal_chat_allowed=portal_chat_allowed,
    )
