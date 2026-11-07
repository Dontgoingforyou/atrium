"""Персональный порядок колонок канбана специалистов.

Revision ID: 0062_spec_board_pref
Revises: 0061_specialist_profile_links
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0062_spec_board_pref"
down_revision = "0061_specialist_profile_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_user_specialist_board_pref",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column("column_order", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_sub", name="uq_portal_user_specialist_board_pref_user"),
    )
    op.create_index(
        "ix_portal_user_specialist_board_pref_user_sub",
        "portal_user_specialist_board_pref",
        ["user_sub"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_portal_user_specialist_board_pref_user_sub",
        table_name="portal_user_specialist_board_pref",
    )
    op.drop_table("portal_user_specialist_board_pref")
