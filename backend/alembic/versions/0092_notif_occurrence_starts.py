"""Снимок времени вхождения события в portal_notification (напоминания).

Revision ID: 0092_notif_occurrence_starts
Revises: 0091_task_jira_outbound
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0092_notif_occurrence_starts"
down_revision = "0091_task_jira_outbound"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_notification",
        sa.Column("calendar_occurrence_starts_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("portal_notification", "calendar_occurrence_starts_at")
