"""Сообщения: редактирование/удаление (updated_at, deleted_for_all_at, hidden для \"у меня\").

Revision ID: 0025_chat_msg_edit_delete  (≤32 символа для alembic_version.version_num)
Revises: 0024_portal_notification
Create Date: 2026-04-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_chat_msg_edit_delete"
down_revision: str | None = "0024_portal_notification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portal_chat_message",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "portal_chat_message",
        sa.Column("deleted_for_all_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_portal_chat_message_deleted_for_all_at",
        "portal_chat_message",
        ["deleted_for_all_at"],
        unique=False,
    )

    op.create_table(
        "portal_chat_message_hidden",
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("message_id", sa.Uuid(), nullable=False),
        sa.Column("chat_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["portal_chat.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["message_id"], ["portal_chat_message.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_sub", "message_id", name="pk_portal_chat_message_hidden"),
    )
    op.create_index("ix_pcmh_user_sub", "portal_chat_message_hidden", ["user_sub"], unique=False)
    op.create_index("ix_pcmh_chat_id", "portal_chat_message_hidden", ["chat_id"], unique=False)
    op.create_index("ix_pcmh_message_id", "portal_chat_message_hidden", ["message_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pcmh_message_id", table_name="portal_chat_message_hidden")
    op.drop_index("ix_pcmh_chat_id", table_name="portal_chat_message_hidden")
    op.drop_index("ix_pcmh_user_sub", table_name="portal_chat_message_hidden")
    op.drop_table("portal_chat_message_hidden")
    op.drop_index("ix_portal_chat_message_deleted_for_all_at", table_name="portal_chat_message")
    op.drop_column("portal_chat_message", "deleted_for_all_at")
    op.drop_column("portal_chat_message", "updated_at")
