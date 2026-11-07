"""Уведомления календаря: cancelled/revoked + context_title; FK event SET NULL.

Revision ID: 0088_calendar_notif_cancelled
Revises: 0087_cal_event_ends_nullable
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0088_calendar_notif_cancelled"
down_revision = "0087_cal_event_ends_nullable"
branch_labels = None
depends_on = None

_CK = (
    "(type IN ('task_mention', 'task_assigned') AND task_id IS NOT NULL AND document_id IS NULL AND "
    "document_comment_id IS NULL AND calendar_event_id IS NULL AND calendar_id IS NULL AND "
    "(type != 'task_mention' OR comment_id IS NOT NULL) AND "
    "(type != 'task_assigned' OR comment_id IS NULL)) OR "
    "(type = 'document_mention' AND task_id IS NULL AND comment_id IS NULL AND "
    "document_id IS NOT NULL AND document_comment_id IS NOT NULL AND "
    "calendar_event_id IS NULL AND calendar_id IS NULL) OR "
    "(type = 'document_trashed' AND task_id IS NULL AND comment_id IS NULL AND "
    "document_id IS NOT NULL AND document_comment_id IS NULL AND "
    "calendar_event_id IS NULL AND calendar_id IS NULL) OR "
    "(type IN ('calendar_invite', 'calendar_reminder', 'calendar_event_updated') AND "
    "calendar_event_id IS NOT NULL AND calendar_id IS NULL AND task_id IS NULL AND comment_id IS NULL AND "
    "document_id IS NULL AND document_comment_id IS NULL) OR "
    "(type = 'calendar_event_cancelled' AND calendar_id IS NULL AND task_id IS NULL AND comment_id IS NULL AND "
    "document_id IS NULL AND document_comment_id IS NULL) OR "
    "(type IN ('calendar_share', 'calendar_share_revoked') AND calendar_id IS NOT NULL AND "
    "calendar_event_id IS NULL AND task_id IS NULL AND comment_id IS NULL AND "
    "document_id IS NULL AND document_comment_id IS NULL)"
)

_CK_OLD = (
    "(type IN ('task_mention', 'task_assigned') AND task_id IS NOT NULL AND document_id IS NULL AND "
    "document_comment_id IS NULL AND calendar_event_id IS NULL AND calendar_id IS NULL AND "
    "(type != 'task_mention' OR comment_id IS NOT NULL) AND "
    "(type != 'task_assigned' OR comment_id IS NULL)) OR "
    "(type = 'document_mention' AND task_id IS NULL AND comment_id IS NULL AND "
    "document_id IS NOT NULL AND document_comment_id IS NOT NULL AND "
    "calendar_event_id IS NULL AND calendar_id IS NULL) OR "
    "(type = 'document_trashed' AND task_id IS NULL AND comment_id IS NULL AND "
    "document_id IS NOT NULL AND document_comment_id IS NULL AND "
    "calendar_event_id IS NULL AND calendar_id IS NULL) OR "
    "(type IN ('calendar_invite', 'calendar_reminder', 'calendar_event_updated') AND "
    "calendar_event_id IS NOT NULL AND calendar_id IS NULL AND task_id IS NULL AND comment_id IS NULL AND "
    "document_id IS NULL AND document_comment_id IS NULL) OR "
    "(type = 'calendar_share' AND calendar_id IS NOT NULL AND calendar_event_id IS NULL AND "
    "task_id IS NULL AND comment_id IS NULL AND document_id IS NULL AND document_comment_id IS NULL)"
)


def upgrade() -> None:
    op.add_column("portal_notification", sa.Column("context_title", sa.String(length=255), nullable=True))
    op.drop_constraint("fk_portal_notification_calendar_event_id", "portal_notification", type_="foreignkey")
    op.create_foreign_key(
        "fk_portal_notification_calendar_event_id",
        "portal_notification",
        "portal_calendar_event",
        ["calendar_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _CK)


def downgrade() -> None:
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _CK_OLD)
    op.drop_constraint("fk_portal_notification_calendar_event_id", "portal_notification", type_="foreignkey")
    op.create_foreign_key(
        "fk_portal_notification_calendar_event_id",
        "portal_notification",
        "portal_calendar_event",
        ["calendar_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_column("portal_notification", "context_title")
