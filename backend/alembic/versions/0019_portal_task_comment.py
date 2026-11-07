"""Комментарии к задачам портала.

Revision ID: 0019_portal_task_comment
Revises: 0018_portal_task_tag
Create Date: 2026-04-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0019_portal_task_comment"
down_revision: str | None = "0018_portal_task_tag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_task_comment",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_sub", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mentions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["task_id"], ["portal_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["portal_task_comment.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_task_comment_task_id", "portal_task_comment", ["task_id"])
    op.create_index("ix_portal_task_comment_parent_id", "portal_task_comment", ["parent_id"])
    op.create_index("ix_portal_task_comment_author_sub", "portal_task_comment", ["author_sub"])


def downgrade() -> None:
    op.drop_index("ix_portal_task_comment_author_sub", table_name="portal_task_comment")
    op.drop_index("ix_portal_task_comment_parent_id", table_name="portal_task_comment")
    op.drop_index("ix_portal_task_comment_task_id", table_name="portal_task_comment")
    op.drop_table("portal_task_comment")
