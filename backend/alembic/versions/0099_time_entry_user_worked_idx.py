"""Составной индекс таймшитов: user_sub + worked_on (list/summary/export).

Revision ID: 0099_time_entry_user_worked_idx
Revises: 0098_telegram_chat_id_unique
"""

from __future__ import annotations

from alembic import op

revision = "0099_time_entry_user_worked_idx"
down_revision = "0098_telegram_chat_id_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_portal_time_entry_user_sub_worked_on",
        "portal_time_entry",
        ["user_sub", "worked_on"],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_time_entry_user_sub_worked_on", table_name="portal_time_entry")
