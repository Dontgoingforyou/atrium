"""Файлы, прикреплённые к задачам: таблица portal_task_file.

Revision ID: 0075_task_file
Revises: 0074_document_comment_media
Create Date: 2026-07-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0075_task_file"
down_revision: str | None = "0074_document_comment_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_task_file",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "task_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_task.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("original_filename", sa.String(512), nullable=False),
        sa.Column("content_type", sa.String(128), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_sub", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_portal_task_file_task_id", "portal_task_file", ["task_id"])
    op.create_index("ix_portal_task_file_uploaded_by_sub", "portal_task_file", ["uploaded_by_sub"])
    op.create_unique_constraint("uq_portal_task_file_storage_key", "portal_task_file", ["storage_key"])


def downgrade() -> None:
    op.drop_constraint("uq_portal_task_file_storage_key", "portal_task_file", type_="unique")
    op.drop_index("ix_portal_task_file_uploaded_by_sub", table_name="portal_task_file")
    op.drop_index("ix_portal_task_file_task_id", table_name="portal_task_file")
    op.drop_table("portal_task_file")
