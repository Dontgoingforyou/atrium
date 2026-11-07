"""Подзадачи: добавление parent_task_id в portal_task.

Revision ID: 0020_task_subtasks
Revises: 0019_portal_task_comment
Create Date: 2026-04-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_task_subtasks"
down_revision: str | None = "0019_portal_task_comment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portal_task",
        sa.Column("parent_task_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_portal_task_parent_task_id",
        "portal_task",
        "portal_task",
        ["parent_task_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_portal_task_parent_task_id", "portal_task", ["parent_task_id"])


def downgrade() -> None:
    op.drop_index("ix_portal_task_parent_task_id", table_name="portal_task")
    op.drop_constraint("fk_portal_task_parent_task_id", "portal_task", type_="foreignkey")
    op.drop_column("portal_task", "parent_task_id")
