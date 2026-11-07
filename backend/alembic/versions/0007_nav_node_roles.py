"""RBAC: таблица portal_nav_node_role (раздел → роль портала).

Revision ID: 0007_nav_node_roles
Revises: 0006_seed_portal_roles
Create Date: 2026-04-07

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_nav_node_roles"
down_revision: str | Sequence[str] | None = "0006_seed_portal_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_nav_node_role",
        sa.Column("node_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["portal_nav_node.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["portal_role.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("node_id", "role_id"),
    )
    op.create_index(
        "ix_portal_nav_node_role_node_id",
        "portal_nav_node_role",
        ["node_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_portal_nav_node_role_node_id",
        table_name="portal_nav_node_role",
    )
    op.drop_table("portal_nav_node_role")
