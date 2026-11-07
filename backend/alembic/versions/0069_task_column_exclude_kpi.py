"""portal_task_column: exclude_from_kpi для исключения колонки из KPI на главной."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0069_task_column_exclude_kpi"
down_revision = "0068_spec_profile_direction"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_task_column",
        sa.Column("exclude_from_kpi", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute(
        sa.text(
            """
            UPDATE portal_task_column
            SET exclude_from_kpi = true
            WHERE nav_node_id IS NULL
              AND status_key IN ('done', 'cancelled')
            """
        )
    )
    op.create_index(
        "ix_portal_task_column_exclude_kpi_status_key",
        "portal_task_column",
        ["exclude_from_kpi", "status_key"],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_task_column_exclude_kpi_status_key", table_name="portal_task_column")
    op.drop_column("portal_task_column", "exclude_from_kpi")
