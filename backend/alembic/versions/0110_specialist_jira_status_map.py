"""portal_specialist_jira_status_map: все статусы колонки Jira → column_id.

Revision ID: 0110_specialist_jira_status_map
Revises: 0109_user_profile_gid
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0110_specialist_jira_status_map"
down_revision = "0109_user_profile_gid"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_specialist_jira_status_map",
        sa.Column("jira_status_id", sa.String(length=20), nullable=False),
        sa.Column("column_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["column_id"], ["portal_specialist_column.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("jira_status_id"),
    )
    op.create_index(
        "ix_portal_specialist_jira_status_map_column_id",
        "portal_specialist_jira_status_map",
        ["column_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_portal_specialist_jira_status_map_column_id", table_name="portal_specialist_jira_status_map")
    op.drop_table("portal_specialist_jira_status_map")
