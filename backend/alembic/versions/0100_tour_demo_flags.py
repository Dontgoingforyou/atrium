"""Флаги is_tour_demo для учебных сущностей онбординга (таймшиты, документы).

Revision ID: 0100_tour_demo_flags
Revises: 0099_time_entry_user_worked_idx
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0100_tour_demo_flags"
down_revision = "0099_time_entry_user_worked_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_time_entry",
        sa.Column("is_tour_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "portal_document",
        sa.Column("is_tour_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("portal_document", "is_tour_demo")
    op.drop_column("portal_time_entry", "is_tour_demo")
