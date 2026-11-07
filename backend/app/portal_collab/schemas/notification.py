from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PortalNotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    recipient_sub: str
    type: str
    task_id: uuid.UUID | None = None
    comment_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    document_comment_id: uuid.UUID | None = None
    calendar_event_id: uuid.UUID | None = None
    calendar_id: uuid.UUID | None = None
    author_sub: str
    created_at: datetime
    read_at: datetime | None

    # Обогащённые поля (заполняются в роутере батчем)
    task_title: str | None = None
    task_priority: str | None = None
    task_due_at: datetime | None = None
    task_status: str | None = None
    document_title: str | None = None
    calendar_event_title: str | None = None
    calendar_event_starts_at: datetime | None = None
    calendar_event_location: str | None = None
    calendar_event_timezone: str | None = None
    calendar_title: str | None = None
    context_title: str | None = None
    author_display_name: str | None = None
    author_avatar_url: str | None = None


class PortalNotificationUnreadCount(BaseModel):
    unread_count: int
