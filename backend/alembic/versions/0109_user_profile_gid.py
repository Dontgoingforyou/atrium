"""portal_user_profile: кэш gid_number отдела SSO.

Revision ID: 0109_user_profile_gid
Revises: 0108_task_due_reminders
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0109_user_profile_gid"
down_revision = "0108_task_due_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_user_profile",
        sa.Column("gid_number", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("portal_user_profile", "gid_number")
