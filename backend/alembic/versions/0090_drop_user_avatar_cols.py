"""Drop user avatar columns; photos live in Effective Admin.

Revision ID: 0090_drop_user_avatar_cols
Revises: 0089_cal_event_color
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0090_drop_user_avatar_cols"
down_revision = "0089_cal_event_color"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("portal_user_profile", "avatar_focal_y")
    op.drop_column("portal_user_profile", "avatar_focal_x")
    op.drop_column("portal_user_profile", "avatar_storage_key")


def downgrade() -> None:
    op.add_column(
        "portal_user_profile",
        sa.Column("avatar_storage_key", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "portal_user_profile",
        sa.Column("avatar_focal_x", sa.Float(), nullable=True),
    )
    op.add_column(
        "portal_user_profile",
        sa.Column("avatar_focal_y", sa.Float(), nullable=True),
    )
