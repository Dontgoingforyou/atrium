"""Составной индекс доски воронки: manager_sub, column_key, position.

Revision ID: 0097_specialist_board_idx
Revises: 0096_doc_comment_media_unique
"""

from __future__ import annotations

from alembic import op

revision = "0097_specialist_board_idx"
down_revision = "0096_doc_comment_media_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_portal_manager_specialist_board",
        "portal_manager_specialist",
        ["manager_sub", "column_key", "position"],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_manager_specialist_board", table_name="portal_manager_specialist")
