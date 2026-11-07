"""Удаление устаревших чатов «только раздела» (без document_id, не ЛС).

Revision ID: 0029_drop_sect_chats
Revises: 0028_nav_node_comnt
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_drop_sect_chats"
down_revision: str | None = "0028_nav_node_comnt"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM portal_chat WHERE nav_node_id IS NOT NULL AND document_id IS NULL AND canonical_dm_key IS NULL"
        )
    )


def downgrade() -> None:
    """Восстановление невозможно — данные удалены."""
