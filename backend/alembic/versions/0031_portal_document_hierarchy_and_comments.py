"""portal_document parent + portal_document_comment

Revision ID: 0031
Revises: 0030
Create Date: 2026-04-27

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0031_portal_doc_hierarchy"
down_revision = "0030_portal_chat_drop_doc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_document",
        sa.Column(
            "parent_document_id",
            sa.Uuid(),
            sa.ForeignKey("portal_document.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_portal_document_parent_document_id",
        "portal_document",
        ["parent_document_id"],
    )

    op.create_table(
        "portal_document_comment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("author_sub", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("mentions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["portal_document.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["portal_document_comment.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_document_comment_document_id", "portal_document_comment", ["document_id"])
    op.create_index("ix_portal_document_comment_parent_id", "portal_document_comment", ["parent_id"])
    op.create_index("ix_portal_document_comment_author_sub", "portal_document_comment", ["author_sub"])


def downgrade() -> None:
    op.drop_index("ix_portal_document_comment_author_sub", table_name="portal_document_comment")
    op.drop_index("ix_portal_document_comment_parent_id", table_name="portal_document_comment")
    op.drop_index("ix_portal_document_comment_document_id", table_name="portal_document_comment")
    op.drop_table("portal_document_comment")
    op.drop_index("ix_portal_document_parent_document_id", table_name="portal_document")
    op.drop_column("portal_document", "parent_document_id")
