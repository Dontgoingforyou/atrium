"""Таблицы ролей портала и назначений пользователям (эпик 5).

Revision ID: 0002_portal_rbac
Revises: 0001_initial
Create Date: 2026-04-03

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_portal_rbac"
down_revision: str | Sequence[str] | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_role",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_portal_role_slug"),
    )
    op.create_table(
        "user_portal_role",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["portal_role.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_sub", "role_id", name="uq_user_portal_role_sub_role"),
    )
    op.create_index("ix_user_portal_role_user_sub", "user_portal_role", ["user_sub"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_user_portal_role_user_sub", table_name="user_portal_role")
    op.drop_table("user_portal_role")
    op.drop_table("portal_role")
