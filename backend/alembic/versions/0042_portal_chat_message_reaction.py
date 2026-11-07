"""Реакции эмодзи на сообщения чата."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0042_chat_msg_reaction"
down_revision = "0041_portal_chat_message_reply"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_chat_message_reaction",
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("emoji", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["portal_chat_message.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("message_id", "user_sub", "emoji"),
    )
    op.create_index(
        "ix_portal_chat_message_reaction_message_id",
        "portal_chat_message_reaction",
        ["message_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_chat_message_reaction_message_id", table_name="portal_chat_message_reaction")
    op.drop_table("portal_chat_message_reaction")
