"""Optimistic-lock version для остальных CAS-сущностей.

Revision ID: 0105_cas_entities
Revises: 0104_task_version
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0105_cas_entities"
down_revision = "0104_task_version"
branch_labels = None
depends_on = None

_TABLES = (
    "portal_specialist_profile",
    "portal_calendar_event",
    "portal_learning_material",
    "portal_checklist",
    "portal_document_comment",
    "portal_task_comment",
    "portal_tag",
    "portal_chat",
    "portal_time_entry",
)


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.drop_column(table, "version")
