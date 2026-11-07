"""Удалить поле document_type из portal_document.

Revision ID: 0036_drop_document_type
Revises: 0035_portal_user_task_board_pref
Create Date: 2026-05-01

Внимание: downgrade восстанавливает столбец и индекс, но данные безвозвратно утеряны.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036_drop_document_type"
down_revision: str | Sequence[str] | None = "0035_portal_user_task_board_pref"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_portal_document_document_type", table_name="portal_document")
    op.drop_column("portal_document", "document_type")


def downgrade() -> None:
    op.add_column(
        "portal_document",
        sa.Column("document_type", sa.String(length=32), nullable=False, server_default="other"),
    )
    op.create_index("ix_portal_document_document_type", "portal_document", ["document_type"])
