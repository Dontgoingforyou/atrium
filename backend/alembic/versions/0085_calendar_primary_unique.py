"""Частичный UNIQUE: один primary-календарь на владельца.

Revision ID: 0085_calendar_primary_unique
Revises: 0084_portal_calendar
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0085_calendar_primary_unique"
down_revision = "0084_portal_calendar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_portal_calendar_owner_primary",
        "portal_calendar",
        ["owner_sub"],
        unique=True,
        postgresql_where=sa.text("is_primary IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index("uq_portal_calendar_owner_primary", table_name="portal_calendar")
