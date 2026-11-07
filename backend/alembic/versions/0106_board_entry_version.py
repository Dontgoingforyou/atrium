"""Optimistic-lock version для portal_manager_specialist.

Revision ID: 0106_board_entry_ver
Revises: 0105_cas_entities
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0106_board_entry_ver"
down_revision = "0105_cas_entities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_manager_specialist",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("portal_manager_specialist", "version")
