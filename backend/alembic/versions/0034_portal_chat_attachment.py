"""portal_chat_attachment: таблица файловых вложений к сообщениям чата.

Revision ID: 0034_portal_chat_attachment
Revises: 0033_portal_embedding
Create Date: 2026-04-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034_portal_chat_attachment"
down_revision: str | Sequence[str] | None = "0033_portal_embedding"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_chat_attachment",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("message_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("chat_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("uploader_sub", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["chat_id"],
            ["portal_chat.id"],
            ondelete="CASCADE",
            name="fk_portal_chat_attachment_chat_id",
        ),
        sa.ForeignKeyConstraint(
            ["message_id"],
            ["portal_chat_message.id"],
            ondelete="CASCADE",
            name="fk_portal_chat_attachment_message_id",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_portal_chat_attachment"),
        sa.UniqueConstraint("storage_key", name="uq_portal_chat_attachment_storage_key"),
    )
    op.create_index("ix_portal_chat_attachment_message_id", "portal_chat_attachment", ["message_id"])
    op.create_index("ix_portal_chat_attachment_chat_id", "portal_chat_attachment", ["chat_id"])
    op.create_index("ix_portal_chat_attachment_uploader_sub", "portal_chat_attachment", ["uploader_sub"])


def downgrade() -> None:
    op.drop_index("ix_portal_chat_attachment_uploader_sub", table_name="portal_chat_attachment")
    op.drop_index("ix_portal_chat_attachment_chat_id", table_name="portal_chat_attachment")
    op.drop_index("ix_portal_chat_attachment_message_id", table_name="portal_chat_attachment")
    op.drop_table("portal_chat_attachment")
