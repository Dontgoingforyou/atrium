from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0061_specialist_profile_links"
down_revision = "0060_portal_specialist_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # portal_specialist_profile — дата рождения, локация, Telegram
    # ------------------------------------------------------------------
    op.create_table(
        "portal_specialist_profile",
        sa.Column(
            "specialist_sub",
            sa.String(255),
            sa.ForeignKey("portal_user_profile.sub", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("birthdate", sa.Date(), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("telegram", sa.String(100), nullable=True),
    )

    # ------------------------------------------------------------------
    # portal_specialist_link — ссылки специалиста (CV и т.д.)
    # ------------------------------------------------------------------
    op.create_table(
        "portal_specialist_link",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "specialist_sub",
            sa.String(255),
            sa.ForeignKey("portal_user_profile.sub", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column(
            "created_by_sub",
            sa.String(255),
            sa.ForeignKey("portal_user_profile.sub", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_portal_specialist_link_specialist_sub",
        "portal_specialist_link",
        ["specialist_sub"],
    )

    # ------------------------------------------------------------------
    # portal_specialist_note — заметки менеджеров о специалисте
    # ------------------------------------------------------------------
    op.create_table(
        "portal_specialist_note",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "specialist_sub",
            sa.String(255),
            sa.ForeignKey("portal_user_profile.sub", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_sub",
            sa.String(255),
            sa.ForeignKey("portal_user_profile.sub", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_portal_specialist_note_specialist_sub",
        "portal_specialist_note",
        ["specialist_sub"],
    )


def downgrade() -> None:
    op.drop_index("ix_portal_specialist_note_specialist_sub", table_name="portal_specialist_note")
    op.drop_table("portal_specialist_note")

    op.drop_index("ix_portal_specialist_link_specialist_sub", table_name="portal_specialist_link")
    op.drop_table("portal_specialist_link")

    op.drop_table("portal_specialist_profile")
