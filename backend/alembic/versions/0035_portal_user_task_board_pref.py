"""Персональные настройки канбана задач (порядок колонок, скрытие, подписи).

Revision ID: 0035_portal_user_task_board_pref
Revises: 0034_portal_chat_attachment
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035_portal_user_task_board_pref"
down_revision: str | Sequence[str] | None = "0034_portal_chat_attachment"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_user_task_board_pref",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column("nav_node_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("scope_key", sa.String(40), nullable=False),
        sa.Column("column_order", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("hidden_status_keys", sa.JSON(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("title_overrides", sa.JSON(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["nav_node_id"], ["portal_nav_node.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_sub", "scope_key", name="uq_portal_user_task_board_pref_scope"),
    )
    op.create_index("ix_portal_user_task_board_pref_user_sub", "portal_user_task_board_pref", ["user_sub"])
    op.create_index("ix_portal_user_task_board_pref_nav_node_id", "portal_user_task_board_pref", ["nav_node_id"])


def downgrade() -> None:
    op.drop_index("ix_portal_user_task_board_pref_nav_node_id", table_name="portal_user_task_board_pref")
    op.drop_index("ix_portal_user_task_board_pref_user_sub", table_name="portal_user_task_board_pref")
    op.drop_table("portal_user_task_board_pref")
