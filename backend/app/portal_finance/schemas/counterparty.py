from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.enums import CounterpartyType


class PortalCounterpartyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=512, description="Наименование контрагента")
    inn: str | None = Field(default=None, max_length=20, description="ИНН (уникальный)")
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=50)
    counterparty_type: CounterpartyType = Field(default=CounterpartyType.VENDOR)
    note: str | None = Field(default=None, max_length=4000)
    is_active: bool = Field(default=True)


class PortalCounterpartyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=512)
    inn: str | None = Field(default=None, max_length=20)
    contact_email: str | None = None
    contact_phone: str | None = None
    counterparty_type: CounterpartyType | None = None
    note: str | None = None
    is_active: bool | None = None


class PortalCounterpartyRead(BaseModel):
    id: uuid.UUID
    name: str
    inn: str | None
    contact_email: str | None
    contact_phone: str | None
    counterparty_type: str
    note: str | None
    is_active: bool
    author_sub: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
