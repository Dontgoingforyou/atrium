"""Пересылка сообщений: ссылка на исходное + снимок автора."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0043_chat_msg_forward"
down_revision = "0042_chat_msg_reaction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_chat_message",
        sa.Column("forwarded_from_message_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "portal_chat_message",
        sa.Column("forwarded_from_author_sub", sa.String(length=255), nullable=True),
    )
    op.create_foreign_key(
        "fk_portal_chat_message_forwarded_from",
        "portal_chat_message",
        "portal_chat_message",
        ["forwarded_from_message_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_portal_chat_message_forwarded_from_message_id",
        "portal_chat_message",
        ["forwarded_from_message_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_portal_chat_message_forwarded_from_message_id", table_name="portal_chat_message")
    op.drop_constraint("fk_portal_chat_message_forwarded_from", "portal_chat_message", type_="foreignkey")
    op.drop_column("portal_chat_message", "forwarded_from_author_sub")
    op.drop_column("portal_chat_message", "forwarded_from_message_id")
