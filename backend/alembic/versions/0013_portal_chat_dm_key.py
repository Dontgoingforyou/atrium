"""DM-чаты: canonical_dm_key для идемпотентного get-or-create.

Добавляет nullable-колонку canonical_dm_key VARCHAR(511) в portal_chat
с UNIQUE-индексом. NULL используют обычные чаты разделов/документов;
для прямых сообщений значение — «{min_sub}|{max_sub}» (алф. порядок).
UNIQUE-ограничение на NULL-значения в PostgreSQL не срабатывает (каждый
NULL считается уникальным), поэтому существующие чаты не затронуты.

Revision ID: 0013_portal_chat_dm_key
Revises: 0012_portal_time_entry
Create Date: 2026-04-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_portal_chat_dm_key"
down_revision: str | None = "0012_portal_time_entry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portal_chat",
        sa.Column("canonical_dm_key", sa.String(511), nullable=True),
    )
    op.create_index(
        "uq_portal_chat_canonical_dm_key",
        "portal_chat",
        ["canonical_dm_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_portal_chat_canonical_dm_key", table_name="portal_chat")
    op.drop_column("portal_chat", "canonical_dm_key")
