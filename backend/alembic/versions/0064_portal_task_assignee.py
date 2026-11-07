"""Несколько исполнителей на задачу (portal_task_assignee).

Revision ID: 0064_portal_task_assignee
Revises: 0063_spec_board_pref_hidden
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0064_portal_task_assignee"
down_revision = "0063_spec_board_pref_hidden"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_task_assignee",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("assignee_sub", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["portal_task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "assignee_sub", name="uq_portal_task_assignee_pair"),
    )
    op.create_index("ix_portal_task_assignee_task_id", "portal_task_assignee", ["task_id"])
    op.create_index("ix_portal_task_assignee_assignee_sub", "portal_task_assignee", ["assignee_sub"])

    op.execute(
        """
        INSERT INTO portal_task_assignee (id, task_id, assignee_sub)
        SELECT gen_random_uuid(), id, assignee_sub
        FROM portal_task
        WHERE assignee_sub IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_portal_task_assignee_assignee_sub", table_name="portal_task_assignee")
    op.drop_index("ix_portal_task_assignee_task_id", table_name="portal_task_assignee")
    op.drop_table("portal_task_assignee")
