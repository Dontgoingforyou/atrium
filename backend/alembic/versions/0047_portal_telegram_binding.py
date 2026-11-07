"""Привязка Telegram-чата к пользователю портала (дубли уведомлений)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0047_portal_telegram_binding"
down_revision = "0046_portal_user_avatar_focal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_telegram_binding",
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("user_sub", name="pk_portal_telegram_binding"),
    )


def downgrade() -> None:
    op.drop_table("portal_telegram_binding")
