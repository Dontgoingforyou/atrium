"""Таблица ярлыков documentLink для левого дерева навигации.

Revision ID: 0077_doc_shortcut
Revises: 0076_dev_docs_root
Create Date: 2026-07-17

Имя ревизии не длиннее 32 символов — колонка alembic_version.version_num VARCHAR(32).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0077_doc_shortcut"
down_revision: str | None = "0076_dev_docs_root"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_document_shortcut",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_document_id", sa.Uuid(), nullable=False),
        sa.Column("target_document_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["portal_document.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_document_id"],
            ["portal_document.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_portal_document_shortcut"),
        sa.UniqueConstraint(
            "source_document_id",
            "target_document_id",
            name="uq_portal_document_shortcut_source_target",
        ),
    )
    op.create_index(
        "ix_portal_document_shortcut_source",
        "portal_document_shortcut",
        ["source_document_id"],
        unique=False,
    )
    op.create_index(
        "ix_portal_document_shortcut_target",
        "portal_document_shortcut",
        ["target_document_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_portal_document_shortcut_target", table_name="portal_document_shortcut")
    op.drop_index("ix_portal_document_shortcut_source", table_name="portal_document_shortcut")
    op.drop_table("portal_document_shortcut")
