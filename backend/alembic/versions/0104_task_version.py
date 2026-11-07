"""Колонка optimistic-lock version у portal_task.

Revision ID: 0104_task_version
Revises: 0103_doc_version
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0104_task_version"
down_revision = "0103_doc_version"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_task",
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("portal_task", "version")
