"""Факт календаря и уведомление без локального события.

Revision ID: 0112_calendar_fact
Revises: 0111_spec_note_parent

Событие живёт в микросервисе. Колокол хранит его id без внешнего ключа
на portal_calendar_event: строки события в Космолете больше нет.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0112_calendar_fact"
down_revision = "0111_spec_note_parent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF EXISTS: на проде FK могли снять вручную при переносе в микросервис.
    op.execute("ALTER TABLE portal_notification DROP CONSTRAINT IF EXISTS fk_portal_notification_calendar_event_id")
    op.create_table(
        "portal_calendar_fact",
        sa.Column("fact_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("fact_id"),
    )
    op.create_index("ix_portal_calendar_fact_event_id", "portal_calendar_fact", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_portal_calendar_fact_event_id", table_name="portal_calendar_fact")
    op.drop_table("portal_calendar_fact")
    op.create_foreign_key(
        "fk_portal_notification_calendar_event_id",
        "portal_notification",
        "portal_calendar_event",
        ["calendar_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
