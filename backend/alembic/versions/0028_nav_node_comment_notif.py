"""Комментарии к разделу (portal_nav_node_comment) + уведомления section_mention.

Revision ID: 0028_nav_node_comnt
Revises: 0027_rbac_idp_groups
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028_nav_node_comnt"
down_revision: str | None = "0027_rbac_idp_groups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_nav_node_comment",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nav_node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_sub", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mentions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["nav_node_id"], ["portal_nav_node.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["portal_nav_node_comment.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_nav_node_comment_nav_node_id", "portal_nav_node_comment", ["nav_node_id"], unique=False)
    op.create_index("ix_portal_nav_node_comment_parent_id", "portal_nav_node_comment", ["parent_id"], unique=False)
    op.create_index("ix_portal_nav_node_comment_author_sub", "portal_nav_node_comment", ["author_sub"], unique=False)

    op.drop_constraint("uq_portal_notification_recipient_comment", "portal_notification", type_="unique")
    op.alter_column(
        "portal_notification",
        "task_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.add_column(
        "portal_notification",
        sa.Column("nav_node_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "portal_notification",
        sa.Column("nav_node_comment_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_portal_notification_nav_node",
        "portal_notification",
        "portal_nav_node",
        ["nav_node_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_portal_notification_nav_node_comment",
        "portal_notification",
        "portal_nav_node_comment",
        ["nav_node_comment_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_portal_notification_nav_node_id", "portal_notification", ["nav_node_id"], unique=False)
    op.create_index(
        "ix_portal_notification_nav_node_comment_id",
        "portal_notification",
        ["nav_node_comment_id"],
        unique=False,
    )

    _ck = (
        "(type IN ('task_mention', 'task_assigned') AND task_id IS NOT NULL AND nav_node_id IS NULL AND "
        "nav_node_comment_id IS NULL AND (type != 'task_mention' OR comment_id IS NOT NULL) AND "
        "(type != 'task_assigned' OR comment_id IS NULL)) OR "
        "(type = 'section_mention' AND task_id IS NULL AND comment_id IS NULL AND "
        "nav_node_id IS NOT NULL AND nav_node_comment_id IS NOT NULL)"
    )
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _ck)

    op.create_index(
        "uq_portal_notif_recipient_task_comment",
        "portal_notification",
        ["recipient_sub", "comment_id"],
        unique=True,
        postgresql_where=sa.text("comment_id IS NOT NULL"),
    )
    op.create_index(
        "uq_portal_notif_recipient_nav_comment",
        "portal_notification",
        ["recipient_sub", "nav_node_comment_id"],
        unique=True,
        postgresql_where=sa.text("nav_node_comment_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_portal_notif_recipient_nav_comment", table_name="portal_notification")
    op.drop_index("uq_portal_notif_recipient_task_comment", table_name="portal_notification")
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    op.drop_index("ix_portal_notification_nav_node_comment_id", table_name="portal_notification")
    op.drop_index("ix_portal_notification_nav_node_id", table_name="portal_notification")
    op.drop_constraint("fk_portal_notification_nav_node_comment", "portal_notification", type_="foreignkey")
    op.drop_constraint("fk_portal_notification_nav_node", "portal_notification", type_="foreignkey")
    op.drop_column("portal_notification", "nav_node_comment_id")
    op.drop_column("portal_notification", "nav_node_id")
    op.alter_column(
        "portal_notification",
        "task_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_unique_constraint(
        "uq_portal_notification_recipient_comment",
        "portal_notification",
        ["recipient_sub", "comment_id"],
    )
    op.drop_index("ix_portal_nav_node_comment_author_sub", table_name="portal_nav_node_comment")
    op.drop_index("ix_portal_nav_node_comment_parent_id", table_name="portal_nav_node_comment")
    op.drop_index("ix_portal_nav_node_comment_nav_node_id", table_name="portal_nav_node_comment")
    op.drop_table("portal_nav_node_comment")
