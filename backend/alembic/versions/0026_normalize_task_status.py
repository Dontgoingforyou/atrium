"""Data migration: normalize portal_task.status and portal_task_column.status_key to lowercase.

Revision ID: 0026_normalize_task_status
Revises: 0025_chat_msg_edit_delete
Create Date: 2026-04-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026_normalize_task_status"
down_revision: str | None = "0025_chat_msg_edit_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE portal_task SET status = LOWER(status) WHERE status != LOWER(status)"))
    op.execute(
        sa.text("UPDATE portal_task_column SET status_key = LOWER(status_key) WHERE status_key != LOWER(status_key)")
    )


def downgrade() -> None:
    pass
