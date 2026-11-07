"""Тип portal_notification.task_comment для комментария без @mention.

Revision ID: 0107_task_comment_notif
Revises: 0106_board_entry_ver
"""

from __future__ import annotations

from alembic import op

revision = "0107_task_comment_notif"
down_revision = "0106_board_entry_ver"
branch_labels = None
depends_on = None

_CK = (
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
    "(type = 'calendar_event_cancelled' AND calendar_id IS NULL AND task_id IS NULL AND comment_id IS NULL AND "
    "document_id IS NULL AND document_comment_id IS NULL) OR "
    "(type IN ('calendar_share', 'calendar_share_revoked') AND calendar_id IS NOT NULL AND "
    "calendar_event_id IS NULL AND task_id IS NULL AND comment_id IS NULL AND "
    "document_id IS NULL AND document_comment_id IS NULL)"
)


def upgrade() -> None:
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _CK)


def downgrade() -> None:
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _CK_OLD)
