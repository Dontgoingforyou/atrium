"""Таблица portal_rich_media для изображений в rich-text."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0070_portal_rich_media"
down_revision = "0069_task_column_exclude_kpi"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_rich_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("uploader_sub", sa.String(length=128), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["document_id"], ["portal_document.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["portal_task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "(task_id IS NOT NULL AND document_id IS NULL) OR (task_id IS NULL AND document_id IS NOT NULL)",
            name="ck_portal_rich_media_single_parent",
        ),
    )
    op.create_index("ix_portal_rich_media_uploader_sub", "portal_rich_media", ["uploader_sub"])
    op.create_index("ix_portal_rich_media_task_id", "portal_rich_media", ["task_id"])
    op.create_index("ix_portal_rich_media_document_id", "portal_rich_media", ["document_id"])


def downgrade() -> None:
    op.drop_index("ix_portal_rich_media_document_id", table_name="portal_rich_media")
    op.drop_index("ix_portal_rich_media_task_id", table_name="portal_rich_media")
    op.drop_index("ix_portal_rich_media_uploader_sub", table_name="portal_rich_media")
    op.drop_table("portal_rich_media")
