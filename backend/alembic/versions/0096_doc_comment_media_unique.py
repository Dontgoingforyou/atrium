"""Уникальность связи комментарий документа ↔ rich-media.

Revision ID: 0096_doc_comment_media_unique
Revises: 0095_task_is_tour_demo
"""

from __future__ import annotations

from alembic import op

revision = "0096_doc_comment_media_unique"
down_revision = "0095_task_is_tour_demo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Дубли связей (если успели накопиться) — оставляем самую новую строку.
    op.execute(
        """
        DELETE FROM portal_document_comment_media a
        USING portal_document_comment_media b
        WHERE a.comment_id = b.comment_id
          AND a.media_id = b.media_id
          AND a.id < b.id
        """
    )
    op.create_unique_constraint(
        "uq_portal_document_comment_media_comment_media",
        "portal_document_comment_media",
        ["comment_id", "media_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_portal_document_comment_media_comment_media",
        "portal_document_comment_media",
        type_="unique",
    )
