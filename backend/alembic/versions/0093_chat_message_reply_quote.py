"""Фрагмент цитаты при ответе на сообщение.

Revision ID: 0093_chat_message_reply_quote
Revises: 0092_notif_occurrence_starts
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0093_chat_message_reply_quote"
down_revision = "0092_notif_occurrence_starts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_chat_message",
        sa.Column("reply_quote_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    # Потеря данных: значения reply_quote_text удаляются вместе с колонкой.
    op.drop_column("portal_chat_message", "reply_quote_text")
