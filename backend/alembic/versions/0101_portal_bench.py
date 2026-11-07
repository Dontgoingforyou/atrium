"""Снимки дашборда бенч и состояние синхронизации Google Таблицы.

Revision ID: 0101_portal_bench
Revises: 0100_tour_demo_flags
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0101_portal_bench"
down_revision = "0100_tour_demo_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_bench_year_snapshot",
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("frozen", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("records", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("year"),
    )
    op.create_index("ix_portal_bench_year_snapshot_frozen", "portal_bench_year_snapshot", ["frozen"])
    op.create_table(
        "portal_bench_sync_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("id = 1", name="ck_portal_bench_sync_state_singleton"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("portal_bench_sync_state")
    op.drop_index("ix_portal_bench_year_snapshot_frozen", table_name="portal_bench_year_snapshot")
    op.drop_table("portal_bench_year_snapshot")
