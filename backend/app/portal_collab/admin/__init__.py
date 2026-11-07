"""Пакет admin-представлений для portal_collab."""

from app.portal_collab.admin.agreements import PortalAgreementAdmin
from app.portal_collab.admin.task_reminders import PortalTaskReminderSentAdmin
from app.portal_collab.admin.tasks import (
    PortalTaskAdmin,
    PortalTaskColumnAdmin,
    PortalTaskCommentAdmin,
    PortalTaskHistoryAdmin,
)
from app.portal_collab.admin.timesheets import PortalTimeEntryAdmin

__all__ = [
    "PortalAgreementAdmin",
    "PortalTaskAdmin",
    "PortalTaskHistoryAdmin",
    "PortalTaskCommentAdmin",
    "PortalTaskColumnAdmin",
    "PortalTaskReminderSentAdmin",
    "PortalTimeEntryAdmin",
]
