"""Календарь портала: таблицы и расширение уведомлений.

Revision ID: 0084_portal_calendar
Revises: 0083_drop_doc_create_position
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0084_portal_calendar"
down_revision = "0083_drop_doc_create_position"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portal_calendar",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_sub", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("color", sa.String(length=32), nullable=False, server_default="#3B82F6"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_calendar_owner_sub", "portal_calendar", ["owner_sub"])

    op.create_table(
        "portal_calendar_member",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("calendar_id", sa.Uuid(), nullable=False),
        sa.Column("user_sub", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["calendar_id"], ["portal_calendar.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("calendar_id", "user_sub", name="uq_portal_calendar_member_user"),
        sa.UniqueConstraint("calendar_id", "email", name="uq_portal_calendar_member_email"),
    )
    op.create_index("ix_portal_calendar_member_calendar_id", "portal_calendar_member", ["calendar_id"])
    op.create_index("ix_portal_calendar_member_user_sub", "portal_calendar_member", ["user_sub"])
    op.create_index("ix_portal_calendar_member_email", "portal_calendar_member", ["email"])

    op.create_table(
        "portal_calendar_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("calendar_id", sa.Uuid(), nullable=False),
        sa.Column("organizer_sub", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("rrule", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["calendar_id"], ["portal_calendar.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_calendar_event_calendar_id", "portal_calendar_event", ["calendar_id"])
    op.create_index("ix_portal_calendar_event_organizer_sub", "portal_calendar_event", ["organizer_sub"])
    op.create_index(
        "ix_portal_calendar_event_range",
        "portal_calendar_event",
        ["calendar_id", "starts_at", "ends_at"],
    )

    op.create_table(
        "portal_calendar_event_override",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("original_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=500), nullable=True),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(["event_id"], ["portal_calendar_event.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "original_start", name="uq_portal_calendar_event_override_start"),
    )
    op.create_index("ix_portal_calendar_event_override_event_id", "portal_calendar_event_override", ["event_id"])

    op.create_table(
        "portal_calendar_attendee",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("user_sub", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["portal_calendar_event.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "email", name="uq_portal_calendar_attendee_email"),
    )
    op.create_index("ix_portal_calendar_attendee_event_id", "portal_calendar_attendee", ["event_id"])
    op.create_index("ix_portal_calendar_attendee_user_sub", "portal_calendar_attendee", ["user_sub"])

    op.create_table(
        "portal_calendar_reminder",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("offset_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("channel", sa.String(length=16), nullable=False, server_default="portal"),
        sa.ForeignKeyConstraint(["event_id"], ["portal_calendar_event.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_calendar_reminder_event_id", "portal_calendar_reminder", ["event_id"])

    op.create_table(
        "portal_calendar_invite_token",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("calendar_id", sa.Uuid(), nullable=True),
        sa.Column("event_id", sa.Uuid(), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["calendar_id"], ["portal_calendar.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], ["portal_calendar_event.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_portal_calendar_invite_token_token", "portal_calendar_invite_token", ["token"], unique=True)
    op.create_index("ix_portal_calendar_invite_token_calendar_id", "portal_calendar_invite_token", ["calendar_id"])
    op.create_index("ix_portal_calendar_invite_token_event_id", "portal_calendar_invite_token", ["event_id"])

    op.create_table(
        "portal_calendar_reminder_sent",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reminder_id", sa.Uuid(), nullable=False),
        sa.Column("occurrence_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recipient_key", sa.String(length=320), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reminder_id"], ["portal_calendar_reminder.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "reminder_id",
            "occurrence_start",
            "recipient_key",
            name="uq_portal_calendar_reminder_sent",
        ),
    )
    op.create_index("ix_portal_calendar_reminder_sent_reminder_id", "portal_calendar_reminder_sent", ["reminder_id"])

    op.add_column("portal_notification", sa.Column("calendar_event_id", sa.Uuid(), nullable=True))
    op.add_column("portal_notification", sa.Column("calendar_id", sa.Uuid(), nullable=True))
    op.create_index("ix_portal_notification_calendar_event_id", "portal_notification", ["calendar_event_id"])
    op.create_index("ix_portal_notification_calendar_id", "portal_notification", ["calendar_id"])
    op.create_foreign_key(
        "fk_portal_notification_calendar_event_id",
        "portal_notification",
        "portal_calendar_event",
        ["calendar_event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_portal_notification_calendar_id",
        "portal_notification",
        "portal_calendar",
        ["calendar_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    _ck = (
        "(type IN ('task_mention', 'task_assigned') AND task_id IS NOT NULL AND document_id IS NULL AND "
        "document_comment_id IS NULL AND calendar_event_id IS NULL AND calendar_id IS NULL AND "
        "(type != 'task_mention' OR comment_id IS NOT NULL) AND "
        "(type != 'task_assigned' OR comment_id IS NULL)) OR "
        "(type = 'document_mention' AND task_id IS NULL AND comment_id IS NULL AND "
        "document_id IS NOT NULL AND document_comment_id IS NOT NULL AND "
        "calendar_event_id IS NULL AND calendar_id IS NULL) OR "
        "(type = 'document_trashed' AND task_id IS NULL AND comment_id IS NULL AND "
        "document_id IS NOT NULL AND document_comment_id IS NULL AND "
        "calendar_event_id IS NULL AND calendar_id IS NULL) OR "
        "(type IN ('calendar_invite', 'calendar_reminder', 'calendar_event_updated') AND "
        "calendar_event_id IS NOT NULL AND calendar_id IS NULL AND task_id IS NULL AND comment_id IS NULL AND "
        "document_id IS NULL AND document_comment_id IS NULL) OR "
        "(type = 'calendar_share' AND calendar_id IS NOT NULL AND calendar_event_id IS NULL AND "
        "task_id IS NULL AND comment_id IS NULL AND document_id IS NULL AND document_comment_id IS NULL)"
    )
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _ck)


def downgrade() -> None:
    op.drop_constraint("ck_portal_notification_context", "portal_notification", type_="check")
    _ck_old = (
        "(type IN ('task_mention', 'task_assigned') AND task_id IS NOT NULL AND document_id IS NULL AND "
        "document_comment_id IS NULL AND "
        "(type != 'task_mention' OR comment_id IS NOT NULL) AND "
        "(type != 'task_assigned' OR comment_id IS NULL)) OR "
        "(type = 'document_mention' AND task_id IS NULL AND comment_id IS NULL AND "
        "document_id IS NOT NULL AND document_comment_id IS NOT NULL) OR "
        "(type = 'document_trashed' AND task_id IS NULL AND comment_id IS NULL AND "
        "document_id IS NOT NULL AND document_comment_id IS NULL)"
    )
    op.create_check_constraint("ck_portal_notification_context", "portal_notification", _ck_old)
    op.drop_constraint("fk_portal_notification_calendar_id", "portal_notification", type_="foreignkey")
    op.drop_constraint("fk_portal_notification_calendar_event_id", "portal_notification", type_="foreignkey")
    op.drop_index("ix_portal_notification_calendar_id", table_name="portal_notification")
    op.drop_index("ix_portal_notification_calendar_event_id", table_name="portal_notification")
    op.drop_column("portal_notification", "calendar_id")
    op.drop_column("portal_notification", "calendar_event_id")

    op.drop_table("portal_calendar_reminder_sent")
    op.drop_table("portal_calendar_invite_token")
    op.drop_table("portal_calendar_reminder")
    op.drop_table("portal_calendar_attendee")
    op.drop_table("portal_calendar_event_override")
    op.drop_table("portal_calendar_event")
    op.drop_table("portal_calendar_member")
    op.drop_table("portal_calendar")
