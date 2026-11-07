"""Транскрибация голосовых сообщений чата: voice_transcript.

Revision ID: 0079_chat_voice_transcript
Revises: 0078_chat_message_pin
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0079_chat_voice_transcript"
down_revision: str | None = "0078_chat_message_pin"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portal_chat_attachment",
        sa.Column("voice_transcript", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("portal_chat_attachment", "voice_transcript")
