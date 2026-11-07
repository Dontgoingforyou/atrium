"""Ответ на сообщение: reply_to_message_id."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0041_portal_chat_message_reply"
down_revision = "0040_doc_comment_notif"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_chat_message",
        sa.Column("reply_to_message_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_portal_chat_message_reply_to_message_id",
        "portal_chat_message",
        ["reply_to_message_id"],
    )
    op.create_foreign_key(
        "fk_portal_chat_message_reply_to_message_id",
        "portal_chat_message",
        "portal_chat_message",
        ["reply_to_message_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_portal_chat_message_reply_to_message_id",
        "portal_chat_message",
        type_="foreignkey",
    )
    op.drop_index("ix_portal_chat_message_reply_to_message_id", table_name="portal_chat_message")
    op.drop_column("portal_chat_message", "reply_to_message_id")
