"""Уведомления календаря без FK на локальные таблицы.

Revision ID: 0113_notif_calendar_no_fk
Revises: 0112_calendar_fact

Календарь и события живут в микросервисе. Колокол хранит id без
внешнего ключа на portal_calendar / portal_calendar_event, чтобы
текст уведомления оставался после переноса и удаления локальных строк.
"""

from __future__ import annotations

from alembic import op

revision = "0113_notif_calendar_no_fk"
down_revision = "0112_calendar_fact"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE portal_notification DROP CONSTRAINT IF EXISTS fk_portal_notification_calendar_id")
    op.execute("ALTER TABLE portal_notification DROP CONSTRAINT IF EXISTS fk_portal_notification_calendar_event_id")


def downgrade() -> None:
    op.create_foreign_key(
        "fk_portal_notification_calendar_id",
        "portal_notification",
        "portal_calendar",
        ["calendar_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_portal_notification_calendar_event_id",
        "portal_notification",
        "portal_calendar_event",
        ["calendar_event_id"],
        ["id"],
        ondelete="SET NULL",
    )
