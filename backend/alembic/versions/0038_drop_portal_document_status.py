"""drop portal_document.status column

Revision ID: 0038_drop_portal_document_status
Revises: 0037_drop_portal_nav_node
Create Date: 2026-05-01

Удалена модель жизненного цикла документа (черновик / опубликован / архив).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0038_drop_portal_document_status"
down_revision = "0037_drop_portal_nav_node"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("portal_document")}
    if "status" not in cols:
        return
    for idx in inspector.get_indexes("portal_document"):
        if "status" in (idx.get("column_names") or []):
            op.drop_index(idx["name"], table_name="portal_document")
    op.drop_column("portal_document", "status")


def downgrade() -> None:
    op.add_column(
        "portal_document",
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default="draft",
        ),
    )
    op.create_index("ix_portal_document_status", "portal_document", ["status"], unique=False)
