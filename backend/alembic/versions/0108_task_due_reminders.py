"""Типы portal_notification.task_due_soon/task_overdue и журнал отправки.

Revision ID: 0108_task_due_reminders
Revises: 0107_task_comment_notif
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0108_task_due_reminders"
down_revision = "0107_task_comment_notif"
branch_labels = None
depends_on = None

_CK = (
    "(type IN ('task_mention', 'task_assigned', 'task_comment', 'task_due_soon', 'task_overdue') AND "
    "task_id IS NOT NULL AND document_id IS NULL AND "
    "document_comment_id IS NULL AND calendar_event_id IS NULL AND calendar_id IS NULL AND "
    "(type != 'task_mention' OR comment_id IS NOT NULL) AND "
    "(type != 'task_comment' OR comment_id IS NOT NULL) AND "
    "(type NOT IN ('task_assigned', 'task_due_soon', 'task_overdue') OR comment_id IS NULL)) OR "
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
    "(type IN ('task_mention', 'task_assigned', 'task_comment') AND task_id IS NOT NULL AND document_id IS NULL AND "
    "document_comment_id IS NULL AND calendar_event_id IS NULL AND calendar_id IS NULL AND "
    "(type != 'task_mention' OR comment_id IS NOT NULL) AND "
    "(type != 'task_comment' OR comment_id IS NOT NULL) AND "
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


def upgrade() -> None:
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _CK)
    op.create_table(
        "portal_task_reminder_sent",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("recipient_sub", sa.String(length=255), nullable=False),
        sa.Column("reminder_kind", sa.String(length=32), nullable=False),
        sa.Column("due_at_snapshot", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["portal_task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "task_id",
            "recipient_sub",
            "reminder_kind",
            "due_at_snapshot",
            name="uq_portal_task_reminder_sent",
        ),
    )
    op.create_index("ix_portal_task_reminder_sent_task_id", "portal_task_reminder_sent", ["task_id"])


def downgrade() -> None:
    op.drop_index("ix_portal_task_reminder_sent_task_id", table_name="portal_task_reminder_sent")
    op.drop_table("portal_task_reminder_sent")
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _CK_OLD)
