"""Упоминания участников в сообщениях чата (JSON)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0053_chat_message_mentions"
down_revision = "0052_task_number_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_chat_message",
        sa.Column("mentions", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("portal_chat_message", "mentions")
