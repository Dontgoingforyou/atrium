"""Название ссылки задачи (portal_task_link.title) становится необязательным.

Revision ID: 0071_task_link_title_optional
Revises: 0070_portal_rich_media
Create Date: 2026-07-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0071_task_link_title_optional"
down_revision: str | None = "0070_portal_rich_media"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "portal_task_link",
        "title",
        existing_type=sa.String(512),
        nullable=True,
    )


def downgrade() -> None:
    op.execute("UPDATE portal_task_link SET title = url WHERE title IS NULL")
    op.alter_column(
        "portal_task_link",
        "title",
        existing_type=sa.String(512),
        nullable=False,
    )
