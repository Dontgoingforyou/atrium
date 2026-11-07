"""Метаданные голосового вложения: длительность и форма волны."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0051_attachment_voice_meta"
down_revision = "0050_portal_web_push"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_chat_attachment",
        sa.Column("voice_duration_seconds", sa.Float(), nullable=True),
    )
    op.add_column(
        "portal_chat_attachment",
        sa.Column("voice_waveform", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("portal_chat_attachment", "voice_waveform")
    op.drop_column("portal_chat_attachment", "voice_duration_seconds")
