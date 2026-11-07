"""Уведомления @ в комментариях к документу (document_mention).

Revision ID: 0040_doc_comment_notif (≤32 символа для alembic_version.version_num)
Revises: 0039_portal_document_icon_emoji
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0040_doc_comment_notif"
down_revision = "0039_portal_document_icon_emoji"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")

    op.add_column(
        "portal_notification",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "portal_notification",
        sa.Column("document_comment_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_portal_notification_document",
        "portal_notification",
        "portal_document",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_portal_notification_document_comment",
        "portal_notification",
        "portal_document_comment",
        ["document_comment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_portal_notification_document_id", "portal_notification", ["document_id"], unique=False)
    op.create_index(
        "ix_portal_notification_document_comment_id",
        "portal_notification",
        ["document_comment_id"],
        unique=False,
    )

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
        "document_id IS NOT NULL AND document_comment_id IS NOT NULL)"
    )
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _ck)

    op.create_index(
        "uq_portal_notif_recipient_document_comment",
        "portal_notification",
        ["recipient_sub", "document_comment_id"],
        unique=True,
        postgresql_where=sa.text("document_comment_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_portal_notif_recipient_document_comment", table_name="portal_notification")
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")

    op.drop_index("ix_portal_notification_document_comment_id", table_name="portal_notification")
    op.drop_index("ix_portal_notification_document_id", table_name="portal_notification")
    op.drop_constraint("fk_portal_notification_document_comment", "portal_notification", type_="foreignkey")
    op.drop_constraint("fk_portal_notification_document", "portal_notification", type_="foreignkey")
    op.drop_column("portal_notification", "document_comment_id")
    op.drop_column("portal_notification", "document_id")

    _ck_old = (
        "(type IN ('task_mention', 'task_assigned') AND task_id IS NOT NULL AND nav_node_id IS NULL AND "
        "nav_node_comment_id IS NULL AND (type != 'task_mention' OR comment_id IS NOT NULL) AND "
        "(type != 'task_assigned' OR comment_id IS NULL)) OR "
        "(type = 'section_mention' AND task_id IS NULL AND comment_id IS NULL AND "
        "nav_node_id IS NOT NULL AND nav_node_comment_id IS NOT NULL)"
    )
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _ck_old)
