"""Денормализованная почта SSO для отображения в админке и API.

Revision ID: 0008_user_emails_denorm
Revises: 0007_nav_node_roles
Create Date: 2026-04-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_user_emails_denorm"
down_revision: str | Sequence[str] | None = "0007_nav_node_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portal_document",
        sa.Column("author_email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "portal_document",
        sa.Column("owner_email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "portal_document_history",
        sa.Column("changed_by_email", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "user_portal_role",
        sa.Column("user_email", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_portal_role", "user_email")
    op.drop_column("portal_document_history", "changed_by_email")
    op.drop_column("portal_document", "owner_email")
    op.drop_column("portal_document", "author_email")
