"""Кастомные колонки канбана: таблица portal_task_column с дефолтными сидами.

Revision ID: 0022_task_columns
Revises: 0021_task_position
Create Date: 2026-04-21
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_task_columns"
down_revision: str | None = "0021_task_position"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEFAULT_COLUMNS = [
    {"status_key": "todo", "title": "К выполнению", "color": "#6131CF", "position": 0},
    {"status_key": "in_progress", "title": "В работе", "color": "#FF6F00", "position": 1},
    {"status_key": "done", "title": "Завершена", "color": "#1A9000", "position": 2},
    {"status_key": "cancelled", "title": "Отменена", "color": "#9B9B9B", "position": 3},
]


def upgrade() -> None:
    op.create_table(
        "portal_task_column",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "nav_node_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_nav_node.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(128), nullable=False),
        sa.Column("color", sa.String(32), nullable=False, server_default="#6131cf"),
        sa.Column("status_key", sa.String(32), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_portal_task_column_nav_node_id", "portal_task_column", ["nav_node_id"])
    op.create_index("ix_portal_task_column_status_key", "portal_task_column", ["status_key"])

    # Сиды дефолтных глобальных колонок (nav_node_id = NULL)
    task_column = sa.table(
        "portal_task_column",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("nav_node_id", sa.Uuid(as_uuid=True)),
        sa.column("title", sa.String),
        sa.column("color", sa.String),
        sa.column("status_key", sa.String),
        sa.column("position", sa.Integer),
    )
    op.bulk_insert(
        task_column,
        [
            {
                "id": uuid.uuid4(),
                "nav_node_id": None,
                "title": row["title"],
                "color": row["color"],
                "status_key": row["status_key"],
                "position": row["position"],
            }
            for row in _DEFAULT_COLUMNS
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_task_column_status_key", table_name="portal_task_column")
    op.drop_index("ix_portal_task_column_nav_node_id", table_name="portal_task_column")
    op.drop_table("portal_task_column")
