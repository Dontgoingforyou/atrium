"""Вложения файлов документов.

Revision ID: 0102_portal_document_file
Revises: 0101_portal_bench
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0102_doc_file"
down_revision = "0101_portal_bench"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_document_file",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("uploaded_by_sub", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["portal_document.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("storage_key", name="uq_portal_document_file_storage_key"),
    )
    op.create_index("ix_portal_document_file_document_id", "portal_document_file", ["document_id"])
    op.create_index("ix_portal_document_file_uploaded_by_sub", "portal_document_file", ["uploaded_by_sub"])


def downgrade() -> None:
    op.drop_index("ix_portal_document_file_uploaded_by_sub", table_name="portal_document_file")
    op.drop_index("ix_portal_document_file_document_id", table_name="portal_document_file")
    op.drop_table("portal_document_file")
