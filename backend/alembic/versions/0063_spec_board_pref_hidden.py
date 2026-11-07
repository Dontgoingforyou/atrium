"""Персональное скрытие колонок канбана специалистов.

Revision ID: 0063_spec_board_pref_hidden
Revises: 0062_spec_board_pref
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0063_spec_board_pref_hidden"
down_revision = "0062_spec_board_pref"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_user_specialist_board_pref",
        sa.Column(
            "hidden_column_keys",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("portal_user_specialist_board_pref", "hidden_column_keys")
