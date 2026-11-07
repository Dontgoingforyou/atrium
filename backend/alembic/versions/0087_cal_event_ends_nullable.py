"""Сделать portal_calendar_event.ends_at опциональным.

Revision ID: 0087_cal_event_ends_nullable
Revises: 0086_task_board_pref_subtasks
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0087_cal_event_ends_nullable"
down_revision = "0086_task_board_pref_subtasks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "portal_calendar_event",
        "ends_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=True,
    )


def downgrade() -> None:
    # Откат: пустые окончания заполняем starts_at, иначе NOT NULL упадёт.
    op.execute(sa.text("UPDATE portal_calendar_event SET ends_at = starts_at WHERE ends_at IS NULL"))
    op.alter_column(
        "portal_calendar_event",
        "ends_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
    )
