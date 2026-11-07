"""Порядок карточек в канбане: добавление position в portal_task.

Revision ID: 0021_task_position
Revises: 0020_task_subtasks
Create Date: 2026-04-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_task_position"
down_revision: str | None = "0020_task_subtasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portal_task",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_portal_task_position", "portal_task", ["position"])


def downgrade() -> None:
    op.drop_index("ix_portal_task_position", table_name="portal_task")
    op.drop_column("portal_task", "position")
