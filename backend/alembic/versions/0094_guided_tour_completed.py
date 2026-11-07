"""Флаг прохождения guided tour в профиле пользователя.

Revision ID: 0094_guided_tour_completed
Revises: 0093_chat_message_reply_quote
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0094_guided_tour_completed"
down_revision = "0093_chat_message_reply_quote"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_user_profile",
        sa.Column(
            "guided_tour_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("portal_user_profile", "guided_tour_completed")
