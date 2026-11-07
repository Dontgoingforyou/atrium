"""Удаление привязки чата к документу (portal_chat.document_id).

Revision ID: 0030_portal_chat_drop_doc
Revises: 0029_drop_sect_chats
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_portal_chat_drop_doc"
down_revision: str | None = "0029_drop_sect_chats"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("DELETE FROM portal_chat WHERE document_id IS NOT NULL"))
    op.drop_constraint("portal_chat_document_id_fkey", "portal_chat", type_="foreignkey")
    op.drop_index(op.f("ix_portal_chat_document_id"), table_name="portal_chat")
    op.drop_column("portal_chat", "document_id")


def downgrade() -> None:
    op.add_column("portal_chat", sa.Column("document_id", sa.Uuid(), nullable=True))
    op.create_index(op.f("ix_portal_chat_document_id"), "portal_chat", ["document_id"], unique=False)
    op.create_foreign_key(
        "portal_chat_document_id_fkey",
        "portal_chat",
        "portal_document",
        ["document_id"],
        ["id"],
        ondelete="SET NULL",
    )
