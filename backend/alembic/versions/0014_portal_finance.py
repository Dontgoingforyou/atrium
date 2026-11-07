"""Финансовый модуль: контрагенты, договоры, счета/акты, платежи.

Таблицы:
- portal_counterparty — справочник контрагентов
- portal_contract     — договоры
- portal_invoice      — счета и акты
- portal_payment      — платежи

Revision ID: 0014_portal_finance
Revises: 0013_portal_chat_dm_key
Create Date: 2026-04-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_portal_finance"
down_revision: str | None = "0013_portal_chat_dm_key"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum-типы PostgreSQL
_counterparty_type = sa.Enum("vendor", "client", "partner", name="counterparty_type_enum")
_contract_type = sa.Enum("template", "active", name="contract_type_enum")
_contract_status = sa.Enum("draft", "active", "completed", "cancelled", name="contract_status_enum")
_invoice_type = sa.Enum("invoice", "act", name="invoice_type_enum")
_invoice_status = sa.Enum("draft", "sent", "paid", "overdue", "cancelled", name="invoice_status_enum")
_payment_category = sa.Enum("contract", "admin_expense", "other", name="payment_category_enum")


def upgrade() -> None:
    # --- portal_counterparty ---
    op.create_table(
        "portal_counterparty",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("inn", sa.String(20), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(50), nullable=True),
        sa.Column("counterparty_type", _counterparty_type, nullable=False, server_default="vendor"),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("author_sub", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_portal_counterparty_name", "portal_counterparty", ["name"])
    op.create_index("ix_portal_counterparty_is_active", "portal_counterparty", ["is_active"])
    op.create_index("ix_portal_counterparty_author_sub", "portal_counterparty", ["author_sub"])
    op.create_index("ix_portal_counterparty_counterparty_type", "portal_counterparty", ["counterparty_type"])
    op.create_unique_constraint("uq_portal_counterparty_inn", "portal_counterparty", ["inn"])

    # --- portal_contract ---
    op.create_table(
        "portal_contract",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("contract_type", _contract_type, nullable=False, server_default="active"),
        sa.Column(
            "counterparty_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_counterparty.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="RUB"),
        sa.Column("start_date", sa.Date, nullable=True),
        sa.Column("end_date", sa.Date, nullable=True),
        sa.Column("status", _contract_status, nullable=False, server_default="draft"),
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
        sa.Column("owner_sub", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_portal_contract_counterparty_id", "portal_contract", ["counterparty_id"])
    op.create_index("ix_portal_contract_nav_node_id", "portal_contract", ["nav_node_id"])
    op.create_index("ix_portal_contract_author_sub", "portal_contract", ["author_sub"])
    op.create_index("ix_portal_contract_status", "portal_contract", ["status"])
    op.create_index("ix_portal_contract_contract_type", "portal_contract", ["contract_type"])

    # --- portal_invoice ---
    op.create_table(
        "portal_invoice",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column(
            "contract_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_contract.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("invoice_type", _invoice_type, nullable=False, server_default="invoice"),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(10), nullable=False, server_default="RUB"),
        sa.Column("issue_date", sa.Date, nullable=True),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("status", _invoice_status, nullable=False, server_default="draft"),
        sa.Column("author_sub", sa.String(255), nullable=False),
        sa.Column(
            "nav_node_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_nav_node.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_portal_invoice_contract_id", "portal_invoice", ["contract_id"])
    op.create_index("ix_portal_invoice_nav_node_id", "portal_invoice", ["nav_node_id"])
    op.create_index("ix_portal_invoice_author_sub", "portal_invoice", ["author_sub"])
    op.create_index("ix_portal_invoice_status", "portal_invoice", ["status"])
    op.create_index("ix_portal_invoice_invoice_type", "portal_invoice", ["invoice_type"])
    op.create_index("ix_portal_invoice_issue_date", "portal_invoice", ["issue_date"])
    op.create_index("ix_portal_invoice_due_date", "portal_invoice", ["due_date"])

    # --- portal_payment ---
    op.create_table(
        "portal_payment",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_invoice.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False, server_default="RUB"),
        sa.Column("paid_at", sa.Date, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("payment_category", _payment_category, nullable=False, server_default="contract"),
        sa.Column("author_sub", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_portal_payment_invoice_id", "portal_payment", ["invoice_id"])
    op.create_index("ix_portal_payment_author_sub", "portal_payment", ["author_sub"])
    op.create_index("ix_portal_payment_paid_at", "portal_payment", ["paid_at"])
    op.create_index("ix_portal_payment_payment_category", "portal_payment", ["payment_category"])


def downgrade() -> None:
    # Удалять в обратном порядке по FK-зависимостям
    op.drop_table("portal_payment")
    op.drop_table("portal_invoice")
    op.drop_table("portal_contract")
    op.drop_table("portal_counterparty")

    _payment_category.drop(op.get_bind(), checkfirst=True)
    _invoice_status.drop(op.get_bind(), checkfirst=True)
    _invoice_type.drop(op.get_bind(), checkfirst=True)
    _contract_status.drop(op.get_bind(), checkfirst=True)
    _contract_type.drop(op.get_bind(), checkfirst=True)
    _counterparty_type.drop(op.get_bind(), checkfirst=True)
