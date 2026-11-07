"""Схемы API календаря."""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.enums import CalendarReminderChannel

_HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _normalize_optional_hex_color(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if not _HEX_COLOR_RE.match(cleaned):
        raise ValueError("Цвет должен быть в формате #RRGGBB")
    return cleaned.upper()


OptionalEventColor = Annotated[str | None, Field(default=None, max_length=32)]


class CalendarCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    color: str = Field(default="#3B82F6", max_length=32)
    timezone: str = Field(default="UTC", max_length=64)

    @field_validator("color")
    @classmethod
    def _color_hex(cls, value: str) -> str:
        normalized = _normalize_optional_hex_color(value)
        if normalized is None:
            raise ValueError("Цвет должен быть в формате #RRGGBB")
        return normalized


class CalendarShowUpdate(BaseModel):
    enabled: bool


class CalendarUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    color: str | None = Field(default=None, max_length=32)
    timezone: str | None = Field(default=None, max_length=64)

    @field_validator("color")
    @classmethod
    def _color_hex(cls, value: str | None) -> str | None:
        return _normalize_optional_hex_color(value)


class CalendarMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_sub: str | None
    email: str | None
    role: str
    created_at: datetime


class CalendarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    owner_sub: str
    owner_label: str | None = None
    title: str
    color: str
    timezone: str
    is_primary: bool
    show_to_other_departments: bool = False
    department_id: str | None = None
    department_label: str | None = None
    my_role: str
    created_at: datetime
    updated_at: datetime
    members: list[CalendarMemberRead] = Field(default_factory=list)


class AttendeeCreate(BaseModel):
    user_sub: str = Field(min_length=1, max_length=255)


class AttendeeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_sub: str | None
    email: str
    status: str
    responded_at: datetime | None
    created_at: datetime


class ReminderCreate(BaseModel):
    offset_minutes: int = Field(default=15, ge=0, le=10080)
    channel: CalendarReminderChannel = CalendarReminderChannel.PORTAL


class ReminderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    offset_minutes: int
    channel: str


_MAX_REMINDERS_PER_EVENT = 5
_MAX_ATTENDEES_PER_EVENT = 100
_MAX_DESCRIPTION_LEN = 10000


class EventCreate(BaseModel):
    calendar_id: uuid.UUID
    title: str = Field(min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=_MAX_DESCRIPTION_LEN)
    location: str | None = Field(default=None, max_length=500)
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None = None
    timezone: str = Field(default="UTC", max_length=64)
    rrule: str | None = Field(default=None, max_length=512)
    color: OptionalEventColor = None
    attendees: list[AttendeeCreate] = Field(min_length=1, max_length=_MAX_ATTENDEES_PER_EVENT)
    reminders: list[ReminderCreate] = Field(default_factory=list, max_length=_MAX_REMINDERS_PER_EVENT)

    @field_validator("color", mode="before")
    @classmethod
    def _color_hex(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("color must be a string")
        return _normalize_optional_hex_color(value)


class EventUpdate(BaseModel):
    expected_version: int = Field(..., ge=1, description="Версия события, прочитанная клиентом (CAS)")
    title: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=_MAX_DESCRIPTION_LEN)
    location: str | None = Field(default=None, max_length=500)
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    timezone: str | None = Field(default=None, max_length=64)
    rrule: str | None = Field(default=None, max_length=512)
    color: OptionalEventColor = None
    attendees: list[AttendeeCreate] | None = Field(default=None, min_length=1, max_length=_MAX_ATTENDEES_PER_EVENT)
    reminders: list[ReminderCreate] | None = Field(
        default=None,
        max_length=_MAX_REMINDERS_PER_EVENT,
    )

    @field_validator("color", mode="before")
    @classmethod
    def _color_hex(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise TypeError("color must be a string")
        return _normalize_optional_hex_color(value)


class EventOccurrenceOverride(BaseModel):
    original_start: AwareDatetime
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    title: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=_MAX_DESCRIPTION_LEN)
    location: str | None = Field(default=None, max_length=500)
    is_cancelled: bool = False

    @model_validator(mode="after")
    def _ends_after_starts(self) -> EventOccurrenceOverride:
        if self.starts_at is not None and self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("Окончание события должно быть позже начала")
        return self


class EventOccurrenceRead(BaseModel):
    """Развёрнутое вхождение (мастер + original_start). Агрегат — не ORM."""

    event_id: uuid.UUID
    calendar_id: uuid.UUID
    calendar_color: str
    color: str | None = None
    original_start: datetime
    starts_at: datetime
    ends_at: datetime | None
    title: str
    description: str | None
    location: str | None
    timezone: str
    rrule: str | None
    organizer_sub: str
    is_cancelled: bool = False
    is_peer_view: bool = False
    attendees: list[AttendeeRead] = Field(default_factory=list)
    reminders: list[ReminderRead] = Field(default_factory=list)


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    calendar_id: uuid.UUID
    organizer_sub: str
    title: str
    description: str | None
    location: str | None
    starts_at: datetime
    ends_at: datetime | None
    timezone: str
    rrule: str | None
    color: str | None = None
    version: int = Field(description="Версия для optimistic locking (CAS)")
    created_at: datetime
    updated_at: datetime
    attendees: list[AttendeeRead] = Field(default_factory=list)
    reminders: list[ReminderRead] = Field(default_factory=list)


class InviteTokenAcceptResponse(BaseModel):
    kind: str
    calendar_id: uuid.UUID | None = None
    event_id: uuid.UUID | None = None
    message: str


class CalendarEventSearchHitRead(BaseModel):
    id: uuid.UUID
    calendar_id: uuid.UUID
    title: str
    starts_at: datetime
    ends_at: datetime | None
    calendar_title: str
    location: str | None = None


class PeerCalendarContextRead(BaseModel):
    calendar_id: uuid.UUID
    owner_sub: str
