"""Закрепление сообщений в чате: pinned_at / pinned_by_sub.

Revision ID: 0078_chat_message_pin
Revises: 0077_doc_shortcut
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0078_chat_message_pin"
down_revision: str | None = "0077_doc_shortcut"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portal_chat_message",
        sa.Column("pinned_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "portal_chat_message",
        sa.Column("pinned_by_sub", sa.String(255), nullable=True),
    )
    op.create_index(
        "ix_portal_chat_message_pinned_at",
        "portal_chat_message",
        ["chat_id", "pinned_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_portal_chat_message_pinned_at", table_name="portal_chat_message")
    op.drop_column("portal_chat_message", "pinned_by_sub")
    op.drop_column("portal_chat_message", "pinned_at")
