"""Время последней активности пользователя в сети (для «был в сети»)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0045_portal_user_last_seen_at"
down_revision = "0044_portal_user_avatar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_user_profile",
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("portal_user_profile", "last_seen_at")
