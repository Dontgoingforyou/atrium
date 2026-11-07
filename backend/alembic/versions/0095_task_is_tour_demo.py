"""Флаг учебной задачи онбординга на portal_task.

Revision ID: 0095_task_is_tour_demo
Revises: 0094_guided_tour_completed
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0095_task_is_tour_demo"
down_revision = "0094_guided_tour_completed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_task",
        sa.Column(
            "is_tour_demo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("portal_task", "is_tour_demo")
