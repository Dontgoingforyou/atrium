"""Общий INSERT уведомления по комментарию (задача или документ), UNIQUE-гонка."""

from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.portal_notification import PortalNotification


def notification_row_id() -> uuid.UUID:
    return uuid.uuid4()


async def existing_comment_notification_id(
    session: AsyncSession,
    *,
    recipient_sub: str,
    comment_id: uuid.UUID | None = None,
    document_comment_id: uuid.UUID | None = None,
) -> uuid.UUID | None:
    stmt = select(PortalNotification.id).where(PortalNotification.recipient_sub == recipient_sub)
    if comment_id is not None:
        stmt = stmt.where(PortalNotification.comment_id == comment_id)
    else:
        stmt = stmt.where(PortalNotification.document_comment_id == document_comment_id)
    return cast(uuid.UUID | None, await session.scalar(stmt))


async def add_comment_notification_row(
    session: AsyncSession,
    row: PortalNotification,
    *,
    recipient_sub: str,
    comment_id: uuid.UUID | None = None,
    document_comment_id: uuid.UUID | None = None,
) -> uuid.UUID | None:
    """INSERT строки комментария; при гонке UNIQUE — вернуть уже существующий id."""
    existing = await existing_comment_notification_id(
        session,
        recipient_sub=recipient_sub,
        comment_id=comment_id,
        document_comment_id=document_comment_id,
    )
    if existing is not None:
        return existing
    try:
        async with session.begin_nested():
            session.add(row)
            await session.flush()
        return row.id
    except IntegrityError:
        return await existing_comment_notification_id(
            session,
            recipient_sub=recipient_sub,
            comment_id=comment_id,
            document_comment_id=document_comment_id,
        )
