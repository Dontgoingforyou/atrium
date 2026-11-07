"""Таймшиты: учёт времени по дням (эпик 15).

Revision ID: 0012_portal_time_entry
Revises: 0011_portal_user_profile
Create Date: 2026-04-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_portal_time_entry"
down_revision: str | None = "0011_portal_user_profile"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_time_entry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("worked_on", sa.Date(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("minutes > 0 AND minutes <= 1440", name="ck_portal_time_entry_minutes_range"),
        sa.ForeignKeyConstraint(["task_id"], ["portal_task.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_time_entry_user_sub", "portal_time_entry", ["user_sub"])
    op.create_index("ix_portal_time_entry_task_id", "portal_time_entry", ["task_id"])
    op.create_index("ix_portal_time_entry_worked_on", "portal_time_entry", ["worked_on"])


def downgrade() -> None:
    op.drop_index("ix_portal_time_entry_worked_on", table_name="portal_time_entry")
    op.drop_index("ix_portal_time_entry_task_id", table_name="portal_time_entry")
    op.drop_index("ix_portal_time_entry_user_sub", table_name="portal_time_entry")
    op.drop_table("portal_time_entry")
