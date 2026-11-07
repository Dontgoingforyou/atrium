from __future__ import annotations

import uuid

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.infrastructure.db.models.portal_calendar import PortalCalendar, PortalCalendarEvent
from app.infrastructure.db.models.portal_document import PortalDocument
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.db.models.portal_task import PortalTask
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_collab.schemas.notification import PortalNotificationRead, PortalNotificationUnreadCount
from app.portal_collab.services import notification as svc
from app.services.user_photo_url import build_user_photo_proxy_url

router = APIRouter(prefix="/portal", tags=["Уведомления"])


async def _enrich_notifications(
    db: DbSession,
    notifications: list[PortalNotification],
) -> list[PortalNotificationRead]:
    """Батч-обогащение: названия задач и имена авторов."""
    if not notifications:
        return []

    task_ids = {n.task_id for n in notifications if n.task_id is not None}
    task_map: dict[uuid.UUID, PortalTask] = {}
    if task_ids:
        task_rows = (await db.execute(select(PortalTask).where(PortalTask.id.in_(task_ids)))).scalars().all()
        task_map = {t.id: t for t in task_rows}

    doc_ids = {n.document_id for n in notifications if n.document_id is not None}
    doc_map: dict[uuid.UUID, PortalDocument] = {}
    if doc_ids:
        doc_rows = (await db.execute(select(PortalDocument).where(PortalDocument.id.in_(doc_ids)))).scalars().all()
        doc_map = {d.id: d for d in doc_rows}

    event_ids = {n.calendar_event_id for n in notifications if n.calendar_event_id is not None}
    event_map: dict[uuid.UUID, PortalCalendarEvent] = {}
    if event_ids:
        event_rows = (
            (await db.execute(select(PortalCalendarEvent).where(PortalCalendarEvent.id.in_(event_ids)))).scalars().all()
        )
        event_map = {e.id: e for e in event_rows}

    calendar_ids = {n.calendar_id for n in notifications if n.calendar_id is not None}
    calendar_map: dict[uuid.UUID, PortalCalendar] = {}
    if calendar_ids:
        cal_rows = (await db.execute(select(PortalCalendar).where(PortalCalendar.id.in_(calendar_ids)))).scalars().all()
        calendar_map = {c.id: c for c in cal_rows}

    author_subs = {n.author_sub for n in notifications}
    profile_rows = (
        (await db.execute(select(PortalUserProfile).where(PortalUserProfile.sub.in_(author_subs)))).scalars().all()
    )
    profile_map = {p.sub: p for p in profile_rows}

    result: list[PortalNotificationRead] = []
    for n in notifications:
        read = PortalNotificationRead.model_validate(n)
        if n.task_id is not None:
            task = task_map.get(n.task_id)
            if task:
                read.task_title = task.title
                read.task_priority = str(task.priority)
                read.task_due_at = task.due_at
                read.task_status = task.status
        if n.document_id is not None:
            d = doc_map.get(n.document_id)
            if d is not None:
                read.document_title = d.title
        if n.calendar_event_id is not None:
            ev = event_map.get(n.calendar_event_id)
            if ev is not None:
                read.calendar_event_title = ev.title
                read.calendar_event_location = ev.location
                read.calendar_event_timezone = ev.timezone
                read.calendar_event_starts_at = (
                    n.calendar_occurrence_starts_at if n.calendar_occurrence_starts_at is not None else ev.starts_at
                )
            elif n.calendar_occurrence_starts_at is not None:
                read.calendar_event_starts_at = n.calendar_occurrence_starts_at
        if n.calendar_id is not None:
            cal = calendar_map.get(n.calendar_id)
            if cal is not None:
                read.calendar_title = cal.title
        context_title = getattr(n, "context_title", None)
        if not read.calendar_event_title and context_title:
            read.calendar_event_title = context_title
        if not read.calendar_title and n.type == "calendar_share_revoked" and context_title:
            read.calendar_title = context_title
        author = profile_map.get(n.author_sub)
        if author:
            read.author_display_name = author.full_name or author.email or author.username
            read.author_avatar_url = build_user_photo_proxy_url(user_sub=author.sub, email=author.email)
        result.append(read)
    return result


@router.get(
    "/notifications",
    summary="Список уведомлений текущего пользователя",
    response_model=list[PortalNotificationRead],
)
async def list_notifications(
    user: CurrentUser,
    db: DbSession,
    unread_only: bool = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[PortalNotificationRead]:
    notifications = await svc.list_notifications(db, user, unread_only=unread_only, skip=skip, limit=limit)
    return await _enrich_notifications(db, notifications)


@router.get(
    "/notifications/unread-count",
    summary="Количество непрочитанных уведомлений",
    response_model=PortalNotificationUnreadCount,
)
async def get_unread_count(
    user: CurrentUser,
    db: DbSession,
) -> PortalNotificationUnreadCount:
    count = await svc.get_unread_count(db, user)
    return PortalNotificationUnreadCount(unread_count=count)


@router.post(
    "/notifications/{notification_id}/read",
    summary="Отметить уведомление прочитанным",
    response_model=PortalNotificationRead,
)
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalNotificationRead:
    notif = await svc.mark_notification_read(db, user, notification_id)
    enriched = await _enrich_notifications(db, [notif])
    return enriched[0]


@router.post(
    "/notifications/mark-all-read",
    summary="Отметить все уведомления прочитанными",
    response_model=PortalNotificationUnreadCount,
)
async def mark_all_notifications_read(
    user: CurrentUser,
    db: DbSession,
) -> PortalNotificationUnreadCount:
    await svc.mark_all_notifications_read(db, user)
    count = await svc.get_unread_count(db, user)
    return PortalNotificationUnreadCount(unread_count=count)


@router.delete(
    "/notifications",
    summary="Удалить все уведомления текущего пользователя",
    status_code=204,
)
async def delete_all_notifications(
    user: CurrentUser,
    db: DbSession,
) -> None:
    await svc.delete_all_notifications(db, user)


@router.delete(
    "/notifications/{notification_id}",
    summary="Удалить уведомление по id",
    status_code=204,
)
async def delete_notification(
    notification_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await svc.delete_notification(db, user, notification_id)
