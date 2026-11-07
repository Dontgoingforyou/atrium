from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import ContractStatus, ContractType


class PortalContractCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    contract_type: ContractType = Field(default=ContractType.ACTIVE)
    counterparty_id: uuid.UUID | None = None
    amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str = Field(default="RUB", max_length=10)
    start_date: date | None = None
    end_date: date | None = None
    status: ContractStatus = Field(default=ContractStatus.DRAFT)
    document_id: uuid.UUID | None = None
    owner_sub: str | None = Field(default=None, max_length=255)


class PortalContractUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    contract_type: ContractType | None = None
    counterparty_id: uuid.UUID | None = None
    amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str | None = Field(default=None, max_length=10)
    start_date: date | None = None
    end_date: date | None = None
    status: ContractStatus | None = None
    document_id: uuid.UUID | None = None
    owner_sub: str | None = None


class PortalCounterpartyShort(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class UserShort(BaseModel):
    sub: str
    full_name: str | None = None
    email: str | None = None
    username: str | None = None

    model_config = {"from_attributes": True}


class PortalContractRead(BaseModel):
    id: uuid.UUID
    title: str
    contract_type: str
    counterparty_id: uuid.UUID | None
    counterparty: PortalCounterpartyShort | None = None
    amount: Decimal | None
    currency: str
    start_date: date | None
    end_date: date | None
    status: str
    document_id: uuid.UUID | None
    author_sub: str
    author_profile: UserShort | None = None
    owner_sub: str | None
    owner_profile: UserShort | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
