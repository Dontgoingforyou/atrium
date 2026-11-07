"""Аватар группового чата (ключ в MinIO + фокус кадра)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0048_portal_chat_avatar"
down_revision = "0047_portal_telegram_binding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("portal_chat", sa.Column("avatar_storage_key", sa.String(length=512), nullable=True))
    op.add_column("portal_chat", sa.Column("avatar_focal_x", sa.Double(), nullable=True))
    op.add_column("portal_chat", sa.Column("avatar_focal_y", sa.Double(), nullable=True))


def downgrade() -> None:
    op.drop_column("portal_chat", "avatar_focal_y")
    op.drop_column("portal_chat", "avatar_focal_x")
    op.drop_column("portal_chat", "avatar_storage_key")
