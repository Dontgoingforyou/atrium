"""Тред комментария специалиста: ответы, упоминания, изображения.

Revision ID: 0111_spec_note_parent
Revises: 0110_specialist_jira_status_map
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0111_spec_note_parent"
down_revision = "0110_specialist_jira_status_map"
branch_labels = None
depends_on = None

_MEDIA_PARENT_CHECK = (
    "(task_id IS NOT NULL AND document_id IS NULL AND specialist_sub IS NULL) OR "
    "(task_id IS NULL AND document_id IS NOT NULL AND specialist_sub IS NULL) OR "
    "(task_id IS NULL AND document_id IS NULL AND specialist_sub IS NOT NULL)"
)
_MEDIA_PARENT_CHECK_PREVIOUS = (
    "(task_id IS NOT NULL AND document_id IS NULL) OR (task_id IS NULL AND document_id IS NOT NULL)"
)


def upgrade() -> None:
    op.add_column(
        "portal_specialist_note",
        sa.Column("parent_id", sa.Uuid(), nullable=True),
    )
    op.create_index(
        "ix_portal_specialist_note_parent_id",
        "portal_specialist_note",
        ["parent_id"],
    )
    op.create_foreign_key(
        "fk_portal_specialist_note_parent_id",
        "portal_specialist_note",
        "portal_specialist_note",
        ["parent_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.add_column(
        "portal_specialist_note",
        sa.Column("mentions", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "portal_specialist_note",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "portal_rich_media",
        sa.Column("specialist_sub", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_portal_rich_media_specialist_sub", "portal_rich_media", ["specialist_sub"])
    op.create_foreign_key(
        "fk_portal_rich_media_specialist_sub",
        "portal_rich_media",
        "portal_user_profile",
        ["specialist_sub"],
        ["sub"],
        ondelete="CASCADE",
    )
    op.drop_constraint("ck_portal_rich_media_single_parent", "portal_rich_media", type_="check")
    op.create_check_constraint(
        "ck_portal_rich_media_single_parent",
        "portal_rich_media",
        _MEDIA_PARENT_CHECK,
    )
    op.create_table(
        "portal_specialist_note_media",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comment_id", sa.Uuid(), nullable=False),
        sa.Column("media_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["portal_specialist_note.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["media_id"], ["portal_rich_media.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("comment_id", "media_id", name="uq_portal_specialist_note_media_comment_media"),
    )
    op.create_index(
        "ix_portal_specialist_note_media_comment_id",
        "portal_specialist_note_media",
        ["comment_id"],
    )
    op.create_index(
        "ix_portal_specialist_note_media_media_id",
        "portal_specialist_note_media",
        ["media_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_specialist_note_media_media_id", table_name="portal_specialist_note_media")
    op.drop_index("ix_portal_specialist_note_media_comment_id", table_name="portal_specialist_note_media")
    op.drop_table("portal_specialist_note_media")
    op.drop_constraint("ck_portal_rich_media_single_parent", "portal_rich_media", type_="check")
    op.create_check_constraint(
        "ck_portal_rich_media_single_parent",
        "portal_rich_media",
        _MEDIA_PARENT_CHECK_PREVIOUS,
    )
    op.drop_constraint("fk_portal_rich_media_specialist_sub", "portal_rich_media", type_="foreignkey")
    op.drop_index("ix_portal_rich_media_specialist_sub", table_name="portal_rich_media")
    op.drop_column("portal_rich_media", "specialist_sub")
    op.drop_column("portal_specialist_note", "version")
    op.drop_column("portal_specialist_note", "mentions")
    op.drop_constraint("fk_portal_specialist_note_parent_id", "portal_specialist_note", type_="foreignkey")
    op.drop_index("ix_portal_specialist_note_parent_id", table_name="portal_specialist_note")
    op.drop_column("portal_specialist_note", "parent_id")
