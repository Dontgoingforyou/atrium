"""Унифицированная модель контента: документы, теги, история изменений (Эпик 7).

Revision ID: 0004_portal_documents
Revises: 0003_portal_nav_tree
Create Date: 2026-04-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_portal_documents"
down_revision: str | Sequence[str] | None = "0003_portal_nav_tree"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- portal_tag --------------------------------------------------------
    op.create_table(
        "portal_tag",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=110), nullable=False),
        sa.Column("color", sa.String(length=7), server_default="#3B82F6", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_portal_tag_slug"),
    )

    # --- portal_document ---------------------------------------------------
    op.create_table(
        "portal_document",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("document_type", sa.String(length=32), nullable=False),
        sa.Column("nav_node_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("author_sub", sa.String(length=255), nullable=False),
        sa.Column("owner_sub", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("body", sa.Text, nullable=True),
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
        sa.ForeignKeyConstraint(
            ["nav_node_id"],
            ["portal_nav_node.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_document_nav_node_id", "portal_document", ["nav_node_id"])
    op.create_index("ix_portal_document_document_type", "portal_document", ["document_type"])
    op.create_index("ix_portal_document_status", "portal_document", ["status"])
    op.create_index("ix_portal_document_author_sub", "portal_document", ["author_sub"])
    op.create_index("ix_portal_document_owner_sub", "portal_document", ["owner_sub"])

    # --- portal_document_tag (join) ----------------------------------------
    op.create_table(
        "portal_document_tag",
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["portal_document.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["portal_tag.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("document_id", "tag_id"),
    )

    # --- portal_document_history -------------------------------------------
    op.create_table(
        "portal_document_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("changed_by_sub", sa.String(length=255), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "diff",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.ForeignKeyConstraint(["document_id"], ["portal_document.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_portal_document_history_document_id",
        "portal_document_history",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_document_history_document_id", table_name="portal_document_history")
    op.drop_table("portal_document_history")
    op.drop_table("portal_document_tag")
    op.drop_index("ix_portal_document_owner_sub", table_name="portal_document")
    op.drop_index("ix_portal_document_author_sub", table_name="portal_document")
    op.drop_index("ix_portal_document_status", table_name="portal_document")
    op.drop_index("ix_portal_document_document_type", table_name="portal_document")
    op.drop_index("ix_portal_document_nav_node_id", table_name="portal_document")
    op.drop_table("portal_document")
    op.drop_table("portal_tag")
