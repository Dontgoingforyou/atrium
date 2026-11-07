"""Ссылки к задачам: таблица portal_task_link.

Revision ID: 0023_task_link
Revises: 0022_task_columns
Create Date: 2026-04-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_task_link"
down_revision: str | None = "0022_task_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_task_link",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "task_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_task.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("created_by_sub", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_portal_task_link_task_id", "portal_task_link", ["task_id"])
    op.create_index("ix_portal_task_link_created_by_sub", "portal_task_link", ["created_by_sub"])


def downgrade() -> None:
    op.drop_index("ix_portal_task_link_created_by_sub", table_name="portal_task_link")
    op.drop_index("ix_portal_task_link_task_id", table_name="portal_task_link")
    op.drop_table("portal_task_link")
