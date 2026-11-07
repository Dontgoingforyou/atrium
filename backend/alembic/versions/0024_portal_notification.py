"""Уведомления @ (portal_notification) + last_read_at для ЛС + is_portal_admin в профиле.

Revision ID: 0024_portal_notification
Revises: 0023_task_link
Create Date: 2026-04-23
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024_portal_notification"
down_revision: str | None = "0023_task_link"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- portal_user_profile: кэш is_portal_admin из IdP (обновляется при логине) ---
    op.add_column(
        "portal_user_profile",
        sa.Column("is_portal_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # --- portal_chat_member: last_read_at для счётчика непрочитанных ЛС ---
    op.add_column(
        "portal_chat_member",
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- portal_notification: уведомления о @ в комментариях к задачам ---
    op.create_table(
        "portal_notification",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recipient_sub", sa.String(255), nullable=False),
        sa.Column("type", sa.String(64), nullable=False, server_default="task_mention"),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("comment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_sub", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["portal_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["comment_id"], ["portal_task_comment.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_notification_recipient_sub", "portal_notification", ["recipient_sub"])
    op.create_index(
        "ix_portal_notification_recipient_read_at",
        "portal_notification",
        ["recipient_sub", "read_at"],
    )
    # Один получатель — одно уведомление на комментарий (идемпотентность)
    op.create_unique_constraint(
        "uq_portal_notification_recipient_comment",
        "portal_notification",
        ["recipient_sub", "comment_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_portal_notification_recipient_comment", "portal_notification", type_="unique")
    op.drop_index("ix_portal_notification_recipient_read_at", table_name="portal_notification")
    op.drop_index("ix_portal_notification_recipient_sub", table_name="portal_notification")
    op.drop_table("portal_notification")
    op.drop_column("portal_chat_member", "last_read_at")
    op.drop_column("portal_user_profile", "is_portal_admin")
