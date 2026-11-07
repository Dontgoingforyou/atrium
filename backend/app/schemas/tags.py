from __future__ import annotations

import uuid

from app.core.color_utils import validate_tag_color_hex
from pydantic import BaseModel, Field, field_validator


class PortalTagRead(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    color: str
    version: int = Field(default=1, description="Версия для optimistic locking (CAS)")

    model_config = {"from_attributes": True}


class PortalTagCreate(BaseModel):
    """Создание тега: slug генерируется на сервере."""

    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#3B82F6", max_length=7)

    @field_validator("name")
    @classmethod
    def name_strip(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("name не может быть пустым")
        return s

    @field_validator("color")
    @classmethod
    def color_format(cls, v: str) -> str:
        return validate_tag_color_hex(v)


class PortalTagUpdate(BaseModel):
    expected_version: int = Field(..., ge=1, description="Версия тега, прочитанная клиентом (CAS)")
    name: str | None = Field(default=None, min_length=1, max_length=100)
    color: str | None = Field(default=None, max_length=7)

    @field_validator("name")
    @classmethod
    def name_strip(cls, v: str | None) -> str | None:
        if v is None:
            return v
        s = v.strip()
        if not s:
            raise ValueError("name не может быть пустым")
        return s

    @field_validator("color", mode="before")
    @classmethod
    def color_format(cls, v: object) -> object:
        if v is None:
            return v
        return validate_tag_color_hex(str(v))
