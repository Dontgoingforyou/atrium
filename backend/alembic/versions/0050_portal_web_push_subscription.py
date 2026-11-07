"""Таблица Web Push подписок для уведомлений о сообщениях в чате."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0050_portal_web_push"
down_revision = "0049_doc_sort_soft_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_web_push_subscription",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("endpoint", name="uq_portal_web_push_subscription_endpoint"),
    )
    op.create_index(
        "ix_portal_web_push_subscription_user_sub",
        "portal_web_push_subscription",
        ["user_sub"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_portal_web_push_subscription_user_sub", table_name="portal_web_push_subscription")
    op.drop_table("portal_web_push_subscription")
