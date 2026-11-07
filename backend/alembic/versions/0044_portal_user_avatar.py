"""Аватар пользователя: ключ объекта в MinIO."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0044_portal_user_avatar"
down_revision = "0043_chat_msg_forward"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_user_profile",
        sa.Column("avatar_storage_key", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("portal_user_profile", "avatar_storage_key")
