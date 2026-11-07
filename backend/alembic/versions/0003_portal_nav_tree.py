"""Дерево разделов навигации портала (эпики 6, 8).

Revision ID: 0003_portal_nav_tree
Revises: 0002_portal_rbac
Create Date: 2026-04-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from app.data.portal_navigation_seed import portal_nav_seed_flat_dicts
from sqlalchemy.dialects import postgresql

revision: str = "0003_portal_nav_tree"
down_revision: str | Sequence[str] | None = "0002_portal_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_nav_node",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("slug", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["portal_nav_node.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_portal_nav_node_slug"),
    )
    op.create_index("ix_portal_nav_node_parent_id", "portal_nav_node", ["parent_id"], unique=False)

    seed = portal_nav_seed_flat_dicts()
    if seed:
        op.bulk_insert(
            sa.table(
                "portal_nav_node",
                sa.column("id", postgresql.UUID(as_uuid=True)),
                sa.column("parent_id", postgresql.UUID(as_uuid=True)),
                sa.column("slug", sa.String()),
                sa.column("title", sa.String()),
                sa.column("sort_order", sa.Integer()),
            ),
            seed,
        )


def downgrade() -> None:
    op.drop_index("ix_portal_nav_node_parent_id", table_name="portal_nav_node")
    op.drop_table("portal_nav_node")
