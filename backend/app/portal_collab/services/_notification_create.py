"""Создание уведомлений (assignments, document, calendar)."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_document_comment import PortalDocumentComment
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_task_reminder_sent import PortalTaskReminderSent
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.services._notification_access import (
    NOTIFICATION_TYPE_ASSIGNED,
    NOTIFICATION_TYPE_CALENDAR_EVENT_CANCELLED,
    NOTIFICATION_TYPE_CALENDAR_EVENT_UPDATED,
    NOTIFICATION_TYPE_CALENDAR_INVITE,
    NOTIFICATION_TYPE_CALENDAR_REMINDER,
    NOTIFICATION_TYPE_CALENDAR_SHARE,
    NOTIFICATION_TYPE_CALENDAR_SHARE_REVOKED,
    NOTIFICATION_TYPE_DOCUMENT_MENTION,
    NOTIFICATION_TYPE_DOCUMENT_TRASHED,
    NOTIFICATION_TYPE_TASK_DUE_SOON,
    NOTIFICATION_TYPE_TASK_OVERDUE,
    TASK_REMINDER_KIND_DUE_SOON,
    TASK_REMINDER_KIND_OVERDUE,
    batch_document_access_check,
    batch_task_access_check,
)
from app.portal_collab.services._notification_rows import add_comment_notification_row, notification_row_id

logger = logging.getLogger(__name__)


async def create_document_mention_notifications(
    session: AsyncSession,
    document: PortalDocument,
    comment: PortalDocumentComment,
    author_sub: str,
) -> dict[str, uuid.UUID]:
    mentioned = set(comment.mentions or []) - {author_sub}
    if not mentioned:
        return {}

    profiles_result = await session.execute(select(PortalUserProfile).where(PortalUserProfile.sub.in_(list(mentioned))))
    profiles_by_sub: dict[str, PortalUserProfile] = {p.sub: p for p in profiles_result.scalars().all()}
    can_access = batch_document_access_check(mentioned, profiles_by_sub)

    notified: dict[str, uuid.UUID] = {}
    for recipient_sub in mentioned:
        if recipient_sub not in profiles_by_sub:
            logger.debug(
                "Пропуск уведомления по документу: нет профиля получателя %s",
                recipient_sub,
            )
            continue
        if recipient_sub not in can_access:
            logger.debug(
                "Пропуск уведомления по документу: получатель %s не имеет доступа к %s",
                recipient_sub,
                document.id,
            )
            continue
        nid = notification_row_id()
        saved = await add_comment_notification_row(
            session,
            PortalNotification(
                id=nid,
                recipient_sub=recipient_sub,
                type=NOTIFICATION_TYPE_DOCUMENT_MENTION,
                document_id=document.id,
                document_comment_id=comment.id,
                author_sub=author_sub,
                created_at=_now_utc(),
            ),
            recipient_sub=recipient_sub,
            document_comment_id=comment.id,
        )
        if saved is not None:
            notified[recipient_sub] = saved
    return notified


async def create_assignment_notification(
    session: AsyncSession,
    task: PortalTask,
    author_sub: str,
    *,
    assignee_sub: str | None = None,
) -> uuid.UUID | None:
    assignee = assignee_sub or task.assignee_sub
    if not assignee or assignee == author_sub:
        return None

    profile = await session.get(PortalUserProfile, assignee)
    profiles_by_sub: dict[str, PortalUserProfile] = {assignee: profile} if profile else {}
    can_access = await batch_task_access_check(session, {assignee}, task, profiles_by_sub)
    if assignee not in can_access:
        logger.debug(
            "Пропуск уведомления о назначении: получатель %s не имеет доступа к задаче %s",
            assignee,
            task.id,
        )
        return None
    nid = notification_row_id()
    session.add(
        PortalNotification(
            id=nid,
            recipient_sub=assignee,
            type=NOTIFICATION_TYPE_ASSIGNED,
            task_id=task.id,
            comment_id=None,
            author_sub=author_sub,
            created_at=_now_utc(),
        )
    )
    return nid


async def create_assignment_notifications(
    session: AsyncSession,
    task: PortalTask,
    author_sub: str,
    assignee_subs: list[str],
) -> dict[str, uuid.UUID]:
    """Батч-версия ``create_assignment_notification`` для нескольких исполнителей.

    Профили и доступ проверяются одним батчем на весь список.
    """
    candidates = {sub for sub in assignee_subs if sub != author_sub}
    if not candidates:
        return {}

    profiles_result = await session.execute(
        select(PortalUserProfile).where(PortalUserProfile.sub.in_(list(candidates))),
    )
    profiles_by_sub: dict[str, PortalUserProfile] = {p.sub: p for p in profiles_result.scalars().all()}
    can_access = await batch_task_access_check(session, candidates, task, profiles_by_sub)

    notified: dict[str, uuid.UUID] = {}
    now = _now_utc()
    for sub in assignee_subs:
        if sub == author_sub:
            continue
        if sub not in can_access:
            logger.debug(
                "Пропуск уведомления о назначении: получатель %s не имеет доступа к задаче %s",
                sub,
                task.id,
            )
            continue
        nid = notification_row_id()
        session.add(
            PortalNotification(
                id=nid,
                recipient_sub=sub,
                type=NOTIFICATION_TYPE_ASSIGNED,
                task_id=task.id,
                comment_id=None,
                author_sub=author_sub,
                created_at=now,
            )
        )
        notified[sub] = nid
    return notified


async def create_document_trashed_notifications(
    session: AsyncSession,
    document_id: uuid.UUID,
    author_sub: str,
) -> dict[str, uuid.UUID]:
    admins = (
        (
            await session.execute(
                select(PortalUserProfile).where(
                    PortalUserProfile.is_portal_admin.is_(True),
                    PortalUserProfile.notify_document_trash.is_(True),
                    PortalUserProfile.sub != author_sub,
                )
            )
        )
        .scalars()
        .all()
    )
    if not admins:
        return {}

    now = _now_utc()
    notified: dict[str, uuid.UUID] = {}
    for profile in admins:
        nid = notification_row_id()
        session.add(
            PortalNotification(
                id=nid,
                recipient_sub=profile.sub,
                type=NOTIFICATION_TYPE_DOCUMENT_TRASHED,
                document_id=document_id,
                author_sub=author_sub,
                created_at=now,
            )
        )
        notified[profile.sub] = nid
    await session.commit()
    return notified


async def notify_document_trashed_bg(document_id: str, author_sub: str) -> None:
    from app.infrastructure.db.session import async_session_factory, skip_background_tasks_using_global_engine
    from app.portal_chat.services.inbox_publish import publish_portal_notification_updates

    if skip_background_tasks_using_global_engine():
        return

    doc_uuid = uuid.UUID(document_id)
    async with async_session_factory() as session:
        notified = await create_document_trashed_notifications(session, doc_uuid, author_sub)
    if notified:
        await publish_portal_notification_updates(
            list(notified.keys()),
            notification_ids_by_sub=notified,
        )


async def create_calendar_invite_notifications(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    author_sub: str,
    recipient_subs: list[str],
    occurrence_starts_at: datetime | None = None,
    context_title: str | None = None,
) -> dict[str, uuid.UUID]:
    """Приглашение на событие (без commit — коммитит вызывающий)."""
    now = _now_utc()
    title = (context_title or "").strip()[:255] or None
    notified: dict[str, uuid.UUID] = {}
    for sub in recipient_subs:
        if sub == author_sub:
            continue
        nid = notification_row_id()
        session.add(
            PortalNotification(
                id=nid,
                recipient_sub=sub,
                type=NOTIFICATION_TYPE_CALENDAR_INVITE,
                calendar_event_id=event_id,
                calendar_occurrence_starts_at=occurrence_starts_at,
                context_title=title,
                author_sub=author_sub,
                created_at=now,
            )
        )
        notified[sub] = nid
    return notified


async def create_calendar_share_notifications(
    session: AsyncSession,
    *,
    calendar_id: uuid.UUID,
    author_sub: str,
    recipient_subs: list[str],
) -> dict[str, uuid.UUID]:
    now = _now_utc()
    notified: dict[str, uuid.UUID] = {}
    for sub in recipient_subs:
        if sub == author_sub:
            continue
        nid = notification_row_id()
        session.add(
            PortalNotification(
                id=nid,
                recipient_sub=sub,
                type=NOTIFICATION_TYPE_CALENDAR_SHARE,
                calendar_id=calendar_id,
                author_sub=author_sub,
                created_at=now,
            )
        )
        notified[sub] = nid
    return notified


async def create_calendar_reminder_notifications(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    author_sub: str,
    recipient_subs: list[str],
    occurrence_starts_at: datetime | None = None,
) -> dict[str, uuid.UUID]:
    """Напоминание о событии — не own-action: организатора (author_sub) не исключаем."""
    now = _now_utc()
    notified: dict[str, uuid.UUID] = {}
    for sub in recipient_subs:
        nid = notification_row_id()
        session.add(
            PortalNotification(
                id=nid,
                recipient_sub=sub,
                type=NOTIFICATION_TYPE_CALENDAR_REMINDER,
                calendar_event_id=event_id,
                calendar_occurrence_starts_at=occurrence_starts_at,
                author_sub=author_sub,
                created_at=now,
            )
        )
        notified[sub] = nid
    return notified


async def create_calendar_event_updated_notifications(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    author_sub: str,
    recipient_subs: list[str],
    occurrence_starts_at: datetime | None = None,
    context_title: str | None = None,
) -> dict[str, uuid.UUID]:
    """Создать уведомления об обновлении. Возвращает recipient_sub → notification_id."""
    now = _now_utc()
    title = (context_title or "").strip()[:255] or None
    notified: dict[str, uuid.UUID] = {}
    for sub in recipient_subs:
        if sub == author_sub:
            continue
        nid = notification_row_id()
        session.add(
            PortalNotification(
                id=nid,
                recipient_sub=sub,
                type=NOTIFICATION_TYPE_CALENDAR_EVENT_UPDATED,
                calendar_event_id=event_id,
                calendar_occurrence_starts_at=occurrence_starts_at,
                context_title=title,
                author_sub=author_sub,
                created_at=now,
            )
        )
        notified[sub] = nid
    return notified


async def create_calendar_event_cancelled_notifications(
    session: AsyncSession,
    *,
    event_id: uuid.UUID,
    author_sub: str,
    recipient_subs: list[str],
    context_title: str,
) -> dict[str, uuid.UUID]:
    """Отмена/удаление события (без commit). context_title сохраняется после SET NULL event_id."""
    now = _now_utc()
    title = (context_title or "").strip()[:255] or "событие"
    notified: dict[str, uuid.UUID] = {}
    for sub in recipient_subs:
        if sub == author_sub:
            continue
        nid = notification_row_id()
        session.add(
            PortalNotification(
                id=nid,
                recipient_sub=sub,
                type=NOTIFICATION_TYPE_CALENDAR_EVENT_CANCELLED,
                calendar_event_id=event_id,
                context_title=title,
                author_sub=author_sub,
                created_at=now,
            )
        )
        notified[sub] = nid
    return notified


async def create_calendar_share_revoked_notifications(
    session: AsyncSession,
    *,
    calendar_id: uuid.UUID,
    author_sub: str,
    recipient_subs: list[str],
    context_title: str | None = None,
) -> dict[str, uuid.UUID]:
    now = _now_utc()
    title = (context_title or "").strip()[:255] or None
    notified: dict[str, uuid.UUID] = {}
    for sub in recipient_subs:
        if sub == author_sub:
            continue
        nid = notification_row_id()
        session.add(
            PortalNotification(
                id=nid,
                recipient_sub=sub,
                type=NOTIFICATION_TYPE_CALENDAR_SHARE_REVOKED,
                calendar_id=calendar_id,
                context_title=title,
                author_sub=author_sub,
                created_at=now,
            )
        )
        notified[sub] = nid
    return notified


_TASK_REMINDER_KIND_TO_TYPE: dict[str, str] = {
    TASK_REMINDER_KIND_DUE_SOON: NOTIFICATION_TYPE_TASK_DUE_SOON,
    TASK_REMINDER_KIND_OVERDUE: NOTIFICATION_TYPE_TASK_OVERDUE,
}


async def create_task_due_reminder_notifications(
    session: AsyncSession,
    task: PortalTask,
    *,
    recipient_subs: list[str],
    reminder_kind: str,
) -> dict[str, uuid.UUID]:
    """Уведомление о сроке + строка sent. Без commit. Организатора не исключаем."""
    notif_type = _TASK_REMINDER_KIND_TO_TYPE.get(reminder_kind)
    if notif_type is None or task.due_at is None or task.id is None:
        return {}
    now = _now_utc()
    notified: dict[str, uuid.UUID] = {}
    for sub in dict.fromkeys(recipient_subs):
        if not sub:
            continue
        nid = notification_row_id()
        try:
            async with session.begin_nested():
                session.add(
                    PortalTaskReminderSent(
                        task_id=task.id,
                        recipient_sub=sub,
                        reminder_kind=reminder_kind,
                        due_at_snapshot=task.due_at,
                        sent_at=now,
                    )
                )
                session.add(
                    PortalNotification(
                        id=nid,
                        recipient_sub=sub,
                        type=notif_type,
                        task_id=task.id,
                        comment_id=None,
                        author_sub=task.creator_sub,
                        created_at=now,
                    )
                )
                await session.flush()
        except IntegrityError:
            logger.info(
                "Пропуск дубля напоминания о сроке: task_id=%s recipient_sub=%s kind=%s",
                task.id,
                sub,
                reminder_kind,
            )
            continue
        notified[sub] = nid
    return notified


async def delete_calendar_event_pre_cancel_notifications(
    session: AsyncSession,
    event_id: uuid.UUID,
) -> None:
    """Снять invite/reminder/updated до удаления события (FK NOT NULL). Без commit."""
    await session.execute(
        delete(PortalNotification).where(
            PortalNotification.calendar_event_id == event_id,
            PortalNotification.type.in_(
                (
                    NOTIFICATION_TYPE_CALENDAR_INVITE,
                    NOTIFICATION_TYPE_CALENDAR_REMINDER,
                    NOTIFICATION_TYPE_CALENDAR_EVENT_UPDATED,
                )
            ),
        )
    )
