"""Создание таблиц воронки специалистов: portal_specialist_column и portal_manager_specialist."""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0059_portal_specialist_board"
down_revision = "0058_portal_te_drop_arch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_specialist_column",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("color", sa.String(30), nullable=False, server_default="#888888"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("key", name="uq_portal_specialist_column_key"),
    )
    op.create_index("ix_portal_specialist_column_position", "portal_specialist_column", ["position"])

    op.create_table(
        "portal_manager_specialist",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("manager_sub", sa.String(255), nullable=False),
        sa.Column("specialist_sub", sa.String(255), nullable=False),
        sa.Column("column_key", sa.String(100), nullable=False, server_default="new"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("manager_sub", "specialist_sub", name="uq_portal_manager_specialist_pair"),
    )
    op.create_index(
        "ix_portal_manager_specialist_manager_sub",
        "portal_manager_specialist",
        ["manager_sub"],
    )
    op.create_index(
        "ix_portal_manager_specialist_specialist_sub",
        "portal_manager_specialist",
        ["specialist_sub"],
    )

    # Дефолтные колонки воронки специалистов
    specialist_column_table = sa.table(
        "portal_specialist_column",
        sa.column("id"),
        sa.column("key"),
        sa.column("title"),
        sa.column("color"),
        sa.column("position"),
    )
    op.bulk_insert(
        specialist_column_table,
        [
            {"id": uuid.uuid4(), "key": "new", "title": "Новичок", "color": "#6366f1", "position": 0},
            {"id": uuid.uuid4(), "key": "reviewing", "title": "На рассмотрении", "color": "#f59e0b", "position": 1},
            {"id": uuid.uuid4(), "key": "cv_sent", "title": "Отправили CV", "color": "#3b82f6", "position": 2},
            {"id": uuid.uuid4(), "key": "hired", "title": "Принят", "color": "#22c55e", "position": 3},
        ],
    )


def downgrade() -> None:
    op.drop_table("portal_manager_specialist")
    op.drop_table("portal_specialist_column")
