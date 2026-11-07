from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.rich_media import RichMediaRead


class DocumentCommentCreate(BaseModel):
    body: str = Field(min_length=0, max_length=4096, default="")
    parent_id: uuid.UUID | None = None
    mentions: list[str] = Field(default_factory=list)
    media_ids: list[uuid.UUID] = Field(default_factory=list)

    @model_validator(mode="after")
    def body_or_media_required(self) -> DocumentCommentCreate:
        if not self.body.strip() and not self.media_ids:
            raise ValueError("Необходимо указать текст или прикрепить изображение")
        return self


class DocumentCommentUpdate(BaseModel):
    expected_version: int = Field(..., ge=1, description="Версия комментария, прочитанная клиентом (CAS)")
    body: str | None = Field(default=None, min_length=1, max_length=4096)
    mentions: list[str] | None = None


class DocumentCommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    parent_id: uuid.UUID | None
    author_sub: str
    author_display_name: str | None = None
    body: str
    mentions: list[str]
    version: int = Field(description="Версия для optimistic locking (CAS)")
    created_at: datetime
    updated_at: datetime
    replies: list[DocumentCommentRead] = []
    media: list[RichMediaRead] = []


DocumentCommentRead.model_rebuild()
