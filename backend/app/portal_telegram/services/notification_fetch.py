from __future__ import annotations

import uuid
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_telegram.services.telegram_text_preview import profile_display

_NOTIFICATION_LOAD_OPTIONS = (
    selectinload(PortalNotification.task),
    selectinload(PortalNotification.document),
    selectinload(PortalNotification.comment),
    selectinload(PortalNotification.document_comment),
    selectinload(PortalNotification.calendar_event),
    selectinload(PortalNotification.calendar),
)


def mention_subs_from_notification(notif: PortalNotification) -> list[str]:
    """Список sub из поля mentions комментария (порядок как в БД)."""
    if notif.type == "task_mention" and notif.comment is not None:
        return list(notif.comment.mentions or [])
    if notif.type == "document_mention" and notif.document_comment is not None:
        return list(notif.document_comment.mentions or [])
    return []


async def fetch_mention_display_labels_longest_first(
    db: AsyncSession,
    mention_subs: list[str],
) -> list[str]:
    """Подписи для сопоставления с текстом @имя (как во фронте), от длинных к коротким."""
    if not mention_subs:
        return []
    unique_order: list[str] = []
    seen: set[str] = set()
    for sub in mention_subs:
        if sub not in seen:
            seen.add(sub)
            unique_order.append(sub)
    stmt = select(PortalUserProfile).where(PortalUserProfile.sub.in_(unique_order))
    rows = (await db.execute(stmt)).scalars().all()
    by_sub = {p.sub: p for p in rows}
    labels: list[str] = []
    for sub in unique_order:
        prof = by_sub.get(sub)
        lab = profile_display(prof, fallback_sub=sub)
        if lab:
            labels.append(lab)
    return sorted(set(labels), key=len, reverse=True)


async def fetch_notification_for_recipient(
    db: AsyncSession,
    recipient_sub: str,
    *,
    notification_id: uuid.UUID | None = None,
) -> PortalNotification | None:
    """Конкретное уведомление по id. Без id — None (без fallback на latest)."""
    if notification_id is None:
        return None
    stmt = (
        select(PortalNotification)
        .where(
            PortalNotification.id == notification_id,
            PortalNotification.recipient_sub == recipient_sub,
        )
        .options(*_NOTIFICATION_LOAD_OPTIONS)
        .limit(1)
    )
    return cast(PortalNotification | None, await db.scalar(stmt))
