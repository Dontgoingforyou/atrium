"""Флаги отображения подзадач на канбане задач.

Revision ID: 0086_task_board_pref_subtasks
Revises: 0085_calendar_primary_unique
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0086_task_board_pref_subtasks"
down_revision = "0085_calendar_primary_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_user_task_board_pref",
        sa.Column("subtasks_flat", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "portal_user_task_board_pref",
        sa.Column("hide_subtasks", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("portal_user_task_board_pref", "hide_subtasks")
    op.drop_column("portal_user_task_board_pref", "subtasks_flat")
