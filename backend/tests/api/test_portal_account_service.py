"""Публичный сервис настроек аккаунта."""

from __future__ import annotations

import pytest
from app.core.exceptions import ForbiddenError
from app.services.portal_account import get_profile
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_profile_raises_when_missing(sqlite_session: AsyncSession) -> None:
    with pytest.raises(ForbiddenError, match="не найден"):
        await get_profile(sqlite_session, "no-profile-sub")
