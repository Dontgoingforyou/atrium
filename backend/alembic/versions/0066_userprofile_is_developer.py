"""portal_user_profile: add is_developer cache column

Revision ID: 0066_portal_user_profile_is_developer
Revises: 0065_notify_document_trash
Create Date: 2026-05-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0066_userprofile_is_developer"
down_revision = "0065_notify_document_trash"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_user_profile",
        sa.Column(
            "is_developer",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("portal_user_profile", "is_developer")
