"""Сервис уведомлений: фасад CRUD и создания."""

from __future__ import annotations

from app.portal_collab.services._notification_create import (
    create_assignment_notification,
    create_assignment_notifications,
    create_calendar_event_cancelled_notifications,
    create_calendar_event_updated_notifications,
    create_calendar_invite_notifications,
    create_calendar_reminder_notifications,
    create_calendar_share_notifications,
    create_calendar_share_revoked_notifications,
    create_document_mention_notifications,
    create_document_trashed_notifications,
    create_task_due_reminder_notifications,
    delete_calendar_event_pre_cancel_notifications,
    notify_document_trashed_bg,
)
from app.portal_collab.services._notification_queries import (
    delete_all_notifications,
    delete_notification,
    get_notification_for_user,
    get_unread_count,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
    recipient_subs_for_task_notifications,
)
from app.portal_collab.services._notification_task import (
    create_comment_notifications,
    create_mention_notifications,
)

__all__ = [
    "create_assignment_notification",
    "create_assignment_notifications",
    "create_comment_notifications",
    "create_calendar_event_cancelled_notifications",
    "create_calendar_event_updated_notifications",
    "create_calendar_invite_notifications",
    "create_calendar_reminder_notifications",
    "create_calendar_share_notifications",
    "create_calendar_share_revoked_notifications",
    "delete_calendar_event_pre_cancel_notifications",
    "create_document_mention_notifications",
    "create_document_trashed_notifications",
    "create_mention_notifications",
    "create_task_due_reminder_notifications",
    "notify_document_trashed_bg",
    "delete_all_notifications",
    "delete_notification",
    "get_notification_for_user",
    "get_unread_count",
    "list_notifications",
    "mark_all_notifications_read",
    "mark_notification_read",
    "recipient_subs_for_task_notifications",
]
