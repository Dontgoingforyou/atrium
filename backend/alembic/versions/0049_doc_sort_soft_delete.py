"""Порядок документов (sort_order) и мягкое удаление (deleted_at).

Имя ревизии не длиннее 32 символов — колонка alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0049_doc_sort_soft_delete"
down_revision = "0048_portal_chat_avatar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_document",
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("portal_document", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("portal_document", sa.Column("deleted_by_sub", sa.String(length=255), nullable=True))
    op.add_column("portal_document", sa.Column("deleted_by_display_name", sa.String(length=255), nullable=True))
    op.add_column("portal_document", sa.Column("deleted_by_email", sa.String(length=255), nullable=True))

    op.create_index("ix_portal_document_deleted_at", "portal_document", ["deleted_at"])

    # Временный индекс под PARTITION BY parent_document_id ORDER BY created_at DESC.
    op.execute(
        sa.text(
            "CREATE INDEX ix_portal_document_mig_parent_created "
            "ON portal_document (parent_document_id, created_at DESC NULLS LAST)"
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE portal_document AS d
            SET sort_order = ranked.rn
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY parent_document_id
                           ORDER BY created_at DESC
                       ) AS rn
                FROM portal_document
            ) AS ranked
            WHERE d.id = ranked.id
            """
        )
    )

    op.create_index(
        "ix_portal_document_parent_sort",
        "portal_document",
        ["parent_document_id", "sort_order"],
    )

    op.execute(sa.text("DROP INDEX IF EXISTS ix_portal_document_mig_parent_created"))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_portal_document_mig_parent_created"))
    op.drop_index("ix_portal_document_parent_sort", table_name="portal_document")
    op.drop_index("ix_portal_document_deleted_at", table_name="portal_document")
    op.drop_column("portal_document", "deleted_by_email")
    op.drop_column("portal_document", "deleted_by_display_name")
    op.drop_column("portal_document", "deleted_by_sub")
    op.drop_column("portal_document", "deleted_at")
    op.drop_column("portal_document", "sort_order")
