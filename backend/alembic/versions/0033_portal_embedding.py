"""portal_embedding: таблица векторных эмбеддингов + pgvector HNSW-индекс.

Revision ID: 0033_portal_embedding
Revises: 0032_portal_tag_unique_name
Create Date: 2026-04-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033_portal_embedding"
down_revision: str | Sequence[str] | None = "0032_portal_tag_unique_name"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Расширение pgvector
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))

    op.create_table(
        "portal_embedding",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(255), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        # Тип vector(1536) создаётся как DDL-строка — pgvector требует расширения
        sa.Column(
            "embedding",
            sa.Text().with_variant(sa.Text(), "sqlite"),  # Placeholder; ниже ALTER TABLE на PG
            nullable=True,
        ),
        sa.Column("meta", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_portal_embedding"),
        sa.UniqueConstraint("entity_type", "entity_id", name="uq_portal_embedding_type_id"),
    )

    # Заменяем placeholder-столбец на настоящий vector(1536)
    op.execute(sa.text("ALTER TABLE portal_embedding DROP COLUMN embedding"))
    op.execute(sa.text("ALTER TABLE portal_embedding ADD COLUMN embedding vector(1536) NOT NULL"))

    op.create_index("ix_portal_embedding_entity_type", "portal_embedding", ["entity_type"])

    # HNSW-индекс для быстрого косинусного поиска
    op.execute(
        sa.text("CREATE INDEX ix_portal_embedding_hnsw ON portal_embedding USING hnsw (embedding vector_cosine_ops)")
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(sa.text("DROP INDEX IF EXISTS ix_portal_embedding_hnsw"))
    op.drop_index("ix_portal_embedding_entity_type", table_name="portal_embedding")
    op.drop_table("portal_embedding")
