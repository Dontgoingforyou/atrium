from __future__ import annotations

import uuid
from datetime import date, datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

from app.portal_specialists.constants import SPECIALIST_NOTE_BODY_MAX_LENGTH
from app.schemas.rich_media import RichMediaRead


class SpecialistProfileRead(BaseModel):
    """Расширенный профиль специалиста, объединяющий PortalUserProfile + PortalSpecialistProfile."""

    specialist_sub: str
    full_name: str | None
    email: str | None
    username: str | None
    birthdate: date | None
    location: str | None
    telegram: str | None
    jira_issue_key: str | None = None
    direction_title: str | None = None
    version: int = Field(default=1, description="Версия для optimistic locking (CAS)")

    model_config = {"from_attributes": True}


class SpecialistProfileUpdate(BaseModel):
    expected_version: int = Field(..., ge=1, description="Версия профиля, прочитанная клиентом (CAS)")
    birthdate: date | None = None
    location: str | None = Field(default=None, max_length=255)
    telegram: str | None = Field(default=None, max_length=100)


class SpecialistLinkRead(BaseModel):
    id: uuid.UUID
    specialist_sub: str
    title: str
    url: str
    created_by_sub: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SpecialistLinkCreate(BaseModel):
    title: str = Field(max_length=255, min_length=1)
    url: str = Field(max_length=2048, min_length=1)

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, value: str) -> str:
        parsed = urlparse(value.strip())
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Укажите корректный адрес (http или https)")
        return value.strip()


class SpecialistNoteRead(BaseModel):
    id: uuid.UUID
    specialist_sub: str
    parent_id: uuid.UUID | None
    author_sub: str
    author_display_name: str | None
    body: str
    mentions: list[str]
    version: int
    created_at: datetime
    updated_at: datetime
    replies: list[SpecialistNoteRead] = Field(default_factory=list)
    media: list[RichMediaRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SpecialistNoteCreate(BaseModel):
    body: str = Field(default="", max_length=SPECIALIST_NOTE_BODY_MAX_LENGTH)
    parent_id: uuid.UUID | None = None
    mentions: list[str] = Field(default_factory=list)
    media_ids: list[uuid.UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def body_or_media_required(self) -> SpecialistNoteCreate:
        if not self.body.strip() and not self.media_ids:
            raise ValueError("Необходимо указать текст или прикрепить изображение")
        return self


class SpecialistNoteUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=SPECIALIST_NOTE_BODY_MAX_LENGTH)
    mentions: list[str] | None = None
    expected_version: int | None = Field(default=None, ge=1)


SpecialistNoteRead.model_rebuild()
