"""UNIQUE на portal_telegram_binding.telegram_chat_id (один чат — один аккаунт).

Revision ID: 0098_telegram_chat_id_unique
Revises: 0097_specialist_board_idx
"""

from __future__ import annotations

from alembic import op

revision = "0098_telegram_chat_id_unique"
down_revision = "0097_specialist_board_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Оставляем самую свежую строку на chat_id; остальные — дубли до unique.
    op.execute(
        """
        DELETE FROM portal_telegram_binding AS a
        USING portal_telegram_binding AS b
        WHERE a.telegram_chat_id = b.telegram_chat_id
          AND a.user_sub <> b.user_sub
          AND (
            a.created_at < b.created_at
            OR (a.created_at = b.created_at AND a.user_sub < b.user_sub)
          )
        """
    )
    op.drop_index("ix_portal_telegram_binding_telegram_chat_id", table_name="portal_telegram_binding")
    op.create_index(
        "uq_portal_telegram_binding_telegram_chat_id",
        "portal_telegram_binding",
        ["telegram_chat_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_portal_telegram_binding_telegram_chat_id", table_name="portal_telegram_binding")
    op.create_index(
        "ix_portal_telegram_binding_telegram_chat_id",
        "portal_telegram_binding",
        ["telegram_chat_id"],
    )
