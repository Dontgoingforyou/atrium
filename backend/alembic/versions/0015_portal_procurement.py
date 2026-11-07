"""Закупки (эпик 17): закупочные заявки.

Таблица:
- portal_procurement_request — заявки на закупку

Revision ID: 0015_portal_procurement
Revises: 0014_portal_finance
Create Date: 2026-04-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PGENUM

revision: str = "0015_portal_procurement"
down_revision: str | None = "0014_portal_finance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# postgresql.ENUM с create_type=False — НЕ пытается создать тип при create_table.
# Тип создаётся явно в upgrade() через DO $$ IF NOT EXISTS.
_procurement_status_col = PGENUM(
    "draft",
    "pending_approval",
    "approved",
    "rejected",
    "in_progress",
    "completed",
    "cancelled",
    name="procurement_status_enum",
    create_type=False,
)


def upgrade() -> None:
    # Создаём enum-тип идемпотентно — пропускаем если уже существует.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'procurement_status_enum') THEN
                CREATE TYPE procurement_status_enum AS ENUM (
                    'draft', 'pending_approval', 'approved', 'rejected',
                    'in_progress', 'completed', 'cancelled'
                );
            END IF;
        END
        $$;
        """
    )

    op.create_table(
        "portal_procurement_request",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "status",
            _procurement_status_col,
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "counterparty_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_counterparty.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="RUB"),
        sa.Column(
            "nav_node_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_nav_node.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "document_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_document.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("author_sub", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("ix_portal_procurement_request_nav_node_id", "portal_procurement_request", ["nav_node_id"])
    op.create_index("ix_portal_procurement_request_status", "portal_procurement_request", ["status"])
    op.create_index("ix_portal_procurement_request_author_sub", "portal_procurement_request", ["author_sub"])
    op.create_index("ix_portal_procurement_request_counterparty_id", "portal_procurement_request", ["counterparty_id"])


def downgrade() -> None:
    op.drop_index("ix_portal_procurement_request_counterparty_id", table_name="portal_procurement_request")
    op.drop_index("ix_portal_procurement_request_author_sub", table_name="portal_procurement_request")
    op.drop_index("ix_portal_procurement_request_status", table_name="portal_procurement_request")
    op.drop_index("ix_portal_procurement_request_nav_node_id", table_name="portal_procurement_request")
    op.drop_table("portal_procurement_request")
    op.execute("DROP TYPE IF EXISTS procurement_status_enum;")
