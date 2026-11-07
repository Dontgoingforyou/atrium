"""Подпись владельца не зависит от скрытия test.* в справочнике."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_calendar.owner_labels import with_owner_labels
from app.portal_calendar.schemas.calendar import CalendarRead
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_owner_label_uses_email_for_test_account(sqlite_session: AsyncSession) -> None:
    sub = str(uuid.uuid4())
    sqlite_session.add(
        PortalUserProfile(
            sub=sub,
            email="test.admin@example.com",
            full_name=None,
            username="admin",
        )
    )
    await sqlite_session.commit()
    calendar = CalendarRead(
        id=uuid.uuid4(),
        owner_sub=sub,
        title="Мой календарь",
        color="#3B82F6",
        timezone="UTC",
        is_primary=True,
        show_to_other_departments=True,
        my_role="viewer",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        members=[],
    )

    enriched = await with_owner_labels(sqlite_session, [calendar])

    assert enriched[0].owner_label == "test.admin@example.com"
