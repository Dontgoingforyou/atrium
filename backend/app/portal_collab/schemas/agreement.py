from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import AgreementStatus


class PortalAgreementCreate(BaseModel):
    body: str = Field(min_length=1)
    status: AgreementStatus | None = None
    source_message_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None


class PortalAgreementUpdate(BaseModel):
    body: str | None = Field(default=None, min_length=1)
    status: AgreementStatus | None = None
    source_message_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    task_id: uuid.UUID | None = None


class PortalAgreementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    body: str
    status: AgreementStatus
    source_message_id: uuid.UUID | None
    source_chat_id: uuid.UUID | None = None
    document_id: uuid.UUID | None
    task_id: uuid.UUID | None
    created_by_sub: str
    created_at: datetime
    updated_at: datetime
