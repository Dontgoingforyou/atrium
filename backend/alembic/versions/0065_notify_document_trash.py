"""Уведомления о корзине документов и настройка в профиле."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0065_notify_document_trash"
down_revision = "0064_portal_task_assignee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_user_profile",
        sa.Column(
            "notify_document_trash",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    _ck = (
        "(type IN ('task_mention', 'task_assigned') AND task_id IS NOT NULL AND nav_node_id IS NULL AND "
        "nav_node_comment_id IS NULL AND document_id IS NULL AND document_comment_id IS NULL AND "
        "(type != 'task_mention' OR comment_id IS NOT NULL) AND "
        "(type != 'task_assigned' OR comment_id IS NULL)) OR "
        "(type = 'section_mention' AND task_id IS NULL AND comment_id IS NULL AND "
        "nav_node_id IS NOT NULL AND nav_node_comment_id IS NOT NULL AND "
        "document_id IS NULL AND document_comment_id IS NULL) OR "
        "(type = 'document_mention' AND task_id IS NULL AND comment_id IS NULL AND "
        "nav_node_id IS NULL AND nav_node_comment_id IS NULL AND "
        "document_id IS NOT NULL AND document_comment_id IS NOT NULL) OR "
        "(type = 'document_trashed' AND task_id IS NULL AND comment_id IS NULL AND "
        "nav_node_id IS NULL AND nav_node_comment_id IS NULL AND "
        "document_id IS NOT NULL AND document_comment_id IS NULL)"
    )
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _ck)


def downgrade() -> None:
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    _ck_old = (
        "(type IN ('task_mention', 'task_assigned') AND task_id IS NOT NULL AND nav_node_id IS NULL AND "
        "nav_node_comment_id IS NULL AND document_id IS NULL AND document_comment_id IS NULL AND "
        "(type != 'task_mention' OR comment_id IS NOT NULL) AND "
        "(type != 'task_assigned' OR comment_id IS NULL)) OR "
        "(type = 'section_mention' AND task_id IS NULL AND comment_id IS NULL AND "
        "nav_node_id IS NOT NULL AND nav_node_comment_id IS NOT NULL AND "
        "document_id IS NULL AND document_comment_id IS NULL) OR "
        "(type = 'document_mention' AND task_id IS NULL AND comment_id IS NULL AND "
        "nav_node_id IS NULL AND nav_node_comment_id IS NULL AND "
        "document_id IS NOT NULL AND document_comment_id IS NOT NULL)"
    )
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _ck_old)
    op.drop_column("portal_user_profile", "notify_document_trash")
