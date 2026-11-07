"""portal_document.icon_emoji — опциональная иконка в дереве навигации.

Revision ID: 0039_portal_document_icon_emoji
Revises: 0038_drop_portal_document_status
Create Date: 2026-05-01
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0039_portal_document_icon_emoji"
down_revision = "0038_drop_portal_document_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("portal_document")}
    if "icon_emoji" in cols:
        return
    op.add_column(
        "portal_document",
        sa.Column("icon_emoji", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("portal_document")}
    if "icon_emoji" not in cols:
        return
    op.drop_column("portal_document", "icon_emoji")
