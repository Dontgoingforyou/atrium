"""Фокус кадра аватара (для object-position в UI)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0046_portal_user_avatar_focal"
down_revision = "0045_portal_user_last_seen_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_user_profile",
        sa.Column("avatar_focal_x", sa.Double(), nullable=True),
    )
    op.add_column(
        "portal_user_profile",
        sa.Column("avatar_focal_y", sa.Double(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("portal_user_profile", "avatar_focal_y")
    op.drop_column("portal_user_profile", "avatar_focal_x")
