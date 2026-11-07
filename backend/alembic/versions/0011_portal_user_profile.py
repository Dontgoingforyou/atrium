"""Профиль пользователя портала (авто-upsert при логине).

Revision ID: 0011_portal_user_profile
Revises: 0010_portal_chat_task_agreement
Create Date: 2026-04-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_portal_user_profile"
down_revision: str | None = "0010_portal_chat_task_agreement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_user_profile",
        sa.Column("sub", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("sub"),
    )
    op.create_index("ix_portal_user_profile_email", "portal_user_profile", ["email"])


def downgrade() -> None:
    op.drop_index("ix_portal_user_profile_email", table_name="portal_user_profile")
    op.drop_table("portal_user_profile")
