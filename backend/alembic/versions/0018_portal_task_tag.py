"""Теги задач: M2M portal_task ↔ portal_tag.

Revision ID: 0018_portal_task_tag
Revises: 0017_learning_material_roles
Create Date: 2026-04-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0018_portal_task_tag"
down_revision: str | None = "0017_learning_material_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_task_tag",
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["portal_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["portal_tag.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("task_id", "tag_id"),
    )
    op.create_index("ix_portal_task_tag_task_id", "portal_task_tag", ["task_id"])
    op.create_index("ix_portal_task_tag_tag_id", "portal_task_tag", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_portal_task_tag_tag_id", table_name="portal_task_tag")
    op.drop_index("ix_portal_task_tag_task_id", table_name="portal_task_tag")
    op.drop_table("portal_task_tag")
