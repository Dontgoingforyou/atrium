"""Таблица избранного портала (пользователь → документ / раздел).

Revision ID: 0009_portal_favorite
Revises: 0008_user_emails_denorm
Create Date: 2026-04-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_portal_favorite"
down_revision: str | Sequence[str] | None = "0008_user_emails_denorm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_favorite",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_sub", "target_type", "target_id", name="uq_portal_favorite_user_target"),
    )
    op.create_index(op.f("ix_portal_favorite_user_sub"), "portal_favorite", ["user_sub"], unique=False)
    op.create_index(op.f("ix_portal_favorite_target_id"), "portal_favorite", ["target_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_portal_favorite_target_id"), table_name="portal_favorite")
    op.drop_index(op.f("ix_portal_favorite_user_sub"), table_name="portal_favorite")
    op.drop_table("portal_favorite")
