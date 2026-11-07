"""Удаление мягкого архива у записей таймшита: колонка is_archived."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision ≤ 32 символов: alembic_version.version_num — VARCHAR(32)
revision = "0058_portal_te_drop_arch"
down_revision = "0057_profile_chat_allowed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_portal_time_entry_is_archived", table_name="portal_time_entry")
    op.drop_column("portal_time_entry", "is_archived")


def downgrade() -> None:
    op.add_column(
        "portal_time_entry",
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_portal_time_entry_is_archived",
        "portal_time_entry",
        ["is_archived"],
        unique=False,
    )
