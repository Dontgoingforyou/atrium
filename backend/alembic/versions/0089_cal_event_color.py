"""Опциональный цвет события (override цвета календаря).

Revision ID: 0089_cal_event_color
Revises: 0088_calendar_notif_cancelled
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0089_cal_event_color"
down_revision = "0088_calendar_notif_cancelled"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_calendar_event",
        sa.Column("color", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("portal_calendar_event", "color")
