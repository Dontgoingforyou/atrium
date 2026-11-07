"""Персональная настройка позиции нового документа (сверху/снизу).

Revision ID: 0072_document_create_position
Revises: 0071_task_link_title_optional
Create Date: 2026-07-05
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0072_document_create_position"
down_revision: str | None = "0071_task_link_title_optional"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "portal_user_profile",
        sa.Column(
            "document_create_position",
            sa.String(16),
            nullable=False,
            server_default="bottom",
        ),
    )
    op.create_check_constraint(
        "ck_portal_user_profile_document_create_position",
        "portal_user_profile",
        "document_create_position IN ('top', 'bottom')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_portal_user_profile_document_create_position",
        "portal_user_profile",
        type_="check",
    )
    op.drop_column("portal_user_profile", "document_create_position")
