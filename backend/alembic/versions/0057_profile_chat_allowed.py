"""Признак доступа к чатам портала (исключение роли students без админа)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0057_profile_chat_allowed"
down_revision = "0056_favorite_attachment_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_user_profile",
        sa.Column(
            "portal_chat_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("portal_user_profile", "portal_chat_allowed")
