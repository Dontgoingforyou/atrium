"""Добавить display_name к назначениям ролей, документам и истории изменений.

Revision ID: 0005_display_names
Revises: 0004_portal_documents
Create Date: 2026-04-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_display_names"
down_revision: str | Sequence[str] | None = "0004_portal_documents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_portal_role",
        sa.Column("user_display_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "portal_document",
        sa.Column("author_display_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "portal_document_history",
        sa.Column("changed_by_display_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("portal_document_history", "changed_by_display_name")
    op.drop_column("portal_document", "author_display_name")
    op.drop_column("user_portal_role", "user_display_name")
