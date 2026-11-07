"""Добавление архивирования и поля task_name в таймшиты."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0054_time_entry_archive"
down_revision = "0053_chat_message_mentions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_time_entry",
        sa.Column("task_name", sa.Text(), nullable=True),
    )
    op.add_column(
        "portal_time_entry",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "ix_portal_time_entry_is_archived",
        "portal_time_entry",
        ["is_archived"],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_time_entry_is_archived", table_name="portal_time_entry")
    op.drop_column("portal_time_entry", "is_archived")
    op.drop_column("portal_time_entry", "task_name")
