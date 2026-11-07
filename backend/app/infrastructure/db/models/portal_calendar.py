"""ORM-модели календаря портала."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import CalendarAttendeeStatus, CalendarMemberRole, CalendarReminderChannel
from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalCalendar(Base):
    """Календарь пользователя: личный или расшаренный."""

    __tablename__ = "portal_calendar"
    __table_args__ = (
        # postgresql_where / sqlite_where: иначе в create_all (SQLite) индекс
        # становится UNIQUE(owner_sub) на все строки и ломает secondary-календари.
        Index(
            "uq_portal_calendar_owner_primary",
            "owner_sub",
            unique=True,
            postgresql_where=text("is_primary IS TRUE"),
            sqlite_where=text("is_primary IS TRUE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    color: Mapped[str] = mapped_column(String(32), nullable=False, default="#3B82F6")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    members: Mapped[list[PortalCalendarMember]] = relationship(
        back_populates="calendar",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    events: Mapped[list[PortalCalendarEvent]] = relationship(
        back_populates="calendar",
        cascade="all, delete-orphan",
        lazy="noload",
    )
    owner_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalCalendar.owner_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
        overlaps="owner_user",
    )
    owner_user: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="foreign(PortalCalendar.owner_sub) == PortalUserProfile.sub",
        lazy="noload",
        overlaps="owner_profile",
    )

    def __str__(self) -> str:
        return self.title


class PortalCalendarMember(Base):
    """Участник календаря (шаринг): owner / editor / viewer."""

    __tablename__ = "portal_calendar_member"
    __table_args__ = (
        UniqueConstraint("calendar_id", "user_sub", name="uq_portal_calendar_member_user"),
        UniqueConstraint("calendar_id", "email", name="uq_portal_calendar_member_email"),
        Index("ix_portal_calendar_member_user_sub", "user_sub"),
        Index("ix_portal_calendar_member_email", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_calendar.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default=CalendarMemberRole.VIEWER.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    calendar: Mapped[PortalCalendar] = relationship(back_populates="members")
    user_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalCalendarMember.user_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )

    def __str__(self) -> str:
        who = self.email or self.user_sub or "?"
        return f"{who} ({self.role})"


class PortalCalendarEvent(Base):
    """Событие календаря (мастер-серия при наличии rrule)."""

    __tablename__ = "portal_calendar_event"
    __table_args__ = (Index("ix_portal_calendar_event_range", "calendar_id", "starts_at", "ends_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    calendar_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_calendar.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organizer_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    rrule: Mapped[str | None] = mapped_column(String(512), nullable=True)
    color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    calendar: Mapped[PortalCalendar] = relationship(back_populates="events")
    attendees: Mapped[list[PortalCalendarAttendee]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    overrides: Mapped[list[PortalCalendarEventOverride]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reminders: Mapped[list[PortalCalendarReminder]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    organizer_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalCalendarEvent.organizer_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
        overlaps="organizer_user",
    )
    organizer_user: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="foreign(PortalCalendarEvent.organizer_sub) == PortalUserProfile.sub",
        lazy="noload",
        overlaps="organizer_profile",
    )

    def __str__(self) -> str:
        return self.title


class PortalCalendarEventOverride(Base):
    """Исключение/правка одного вхождения повторяющегося события."""

    __tablename__ = "portal_calendar_event_override"
    __table_args__ = (UniqueConstraint("event_id", "original_start", name="uq_portal_calendar_event_override_start"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_calendar_event.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    original_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    event: Mapped[PortalCalendarEvent] = relationship(back_populates="overrides")

    def __str__(self) -> str:
        label = self.title or ("отменено" if self.is_cancelled else "override")
        return f"{label} @ {self.original_start}"


class PortalCalendarAttendee(Base):
    """Участник события (гость портала или внешний email)."""

    __tablename__ = "portal_calendar_attendee"
    __table_args__ = (
        UniqueConstraint("event_id", "email", name="uq_portal_calendar_attendee_email"),
        Index("ix_portal_calendar_attendee_user_sub", "user_sub"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_calendar_event.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=CalendarAttendeeStatus.ACCEPTED.value)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    event: Mapped[PortalCalendarEvent] = relationship(back_populates="attendees")
    user_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalCalendarAttendee.user_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )

    def __str__(self) -> str:
        return self.email


class PortalCalendarReminder(Base):
    """Напоминание до начала события (смещение в минутах)."""

    __tablename__ = "portal_calendar_reminder"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_calendar_event.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default=CalendarReminderChannel.PORTAL.value)

    event: Mapped[PortalCalendarEvent] = relationship(back_populates="reminders")

    def __str__(self) -> str:
        return f"−{self.offset_minutes} мин ({self.channel})"


class PortalCalendarInviteToken(Base):
    """Токен принятия шаринга календаря или приглашения на событие по email."""

    __tablename__ = "portal_calendar_invite_token"
    __table_args__ = (Index("ix_portal_calendar_invite_token_token", "token", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(64), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    calendar_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_calendar.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_calendar_event.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str | None] = mapped_column(String(16), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    calendar: Mapped[PortalCalendar | None] = relationship(foreign_keys=[calendar_id], lazy="select")
    event: Mapped[PortalCalendarEvent | None] = relationship(foreign_keys=[event_id], lazy="select")

    def __str__(self) -> str:
        return f"{self.kind}:{self.email}"


class PortalCalendarReminderSent(Base):
    """Идемпотентность отправки напоминаний по вхождению."""

    __tablename__ = "portal_calendar_reminder_sent"
    __table_args__ = (
        UniqueConstraint(
            "reminder_id",
            "occurrence_start",
            "recipient_key",
            name="uq_portal_calendar_reminder_sent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reminder_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_calendar_reminder.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    occurrence_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recipient_key: Mapped[str] = mapped_column(String(320), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reminder: Mapped[PortalCalendarReminder] = relationship(foreign_keys=[reminder_id], lazy="select")
    # recipient_key = "sub:<uuid>" | "email:<addr>" — профиль только для portal-пользователей
    recipient_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin=(
            "and_("
            "PortalCalendarReminderSent.recipient_key.like('sub:%'), "
            "foreign(PortalUserProfile.sub) == func.substr(PortalCalendarReminderSent.recipient_key, 5)"
            ")"
        ),
        viewonly=True,
        lazy="selectin",
    )

    def __str__(self) -> str:
        return f"{self.recipient_key} @ {self.occurrence_start}"
