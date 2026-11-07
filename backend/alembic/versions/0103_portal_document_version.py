"""Колонка optimistic-lock version у portal_document.

Revision ID: 0103_doc_version
Revises: 0102_doc_file
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0103_doc_version"
down_revision = "0102_doc_file"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_document",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("portal_document", "version")
