"""Индексы для избранного и очистки осиротевших вложений."""

from __future__ import annotations

from alembic import op

revision = "0056_favorite_attachment_indexes"
down_revision = "0055_missing_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Список избранного пользователя: WHERE user_sub ORDER BY created_at DESC
    op.create_index(
        "ix_portal_favorite_user_sub_created_at",
        "portal_favorite",
        ["user_sub", "created_at"],
    )

    # Очистка осиротевших вложений (message_id IS NULL) по created_at
    # partial index: фильтрует только unlinked строки, не раздувая индекс прикреплёнными
    op.create_index(
        "ix_portal_chat_attachment_orphan_created_at",
        "portal_chat_attachment",
        ["created_at"],
        postgresql_where="message_id IS NULL",
    )


def downgrade() -> None:
    op.drop_index("ix_portal_chat_attachment_orphan_created_at", table_name="portal_chat_attachment")
    op.drop_index("ix_portal_favorite_user_sub_created_at", table_name="portal_favorite")
