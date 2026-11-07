"""Добавление таблицы статусов специалистов и FK status_id в portal_manager_specialist."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0060_portal_specialist_status"
down_revision = "0059_portal_specialist_board"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_specialist_status",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("color", sa.String(30), nullable=False, server_default="#888888"),
        sa.UniqueConstraint("title", name="uq_portal_specialist_status_title"),
    )

    op.add_column(
        "portal_manager_specialist",
        sa.Column(
            "status_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_specialist_status.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("portal_manager_specialist", "status_id")
    op.drop_table("portal_specialist_status")
