"""Таблица portal_document_comment_media: изображения в комментариях к документам.

Revision ID: 0074_document_comment_media
Revises: 0073_task_comment_media
Create Date: 2026-07-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0074_document_comment_media"
down_revision: str | None = "0073_task_comment_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_document_comment_media",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("comment_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("media_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["comment_id"],
            ["portal_document_comment.id"],
            ondelete="CASCADE",
            name="fk_portal_document_comment_media_comment_id",
        ),
        sa.ForeignKeyConstraint(
            ["media_id"],
            ["portal_rich_media.id"],
            ondelete="CASCADE",
            name="fk_portal_document_comment_media_media_id",
        ),
    )
    op.create_index(
        "ix_portal_document_comment_media_comment_id",
        "portal_document_comment_media",
        ["comment_id"],
    )
    op.create_index(
        "ix_portal_document_comment_media_media_id",
        "portal_document_comment_media",
        ["media_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_document_comment_media_media_id", "portal_document_comment_media")
    op.drop_index("ix_portal_document_comment_media_comment_id", "portal_document_comment_media")
    op.drop_table("portal_document_comment_media")
