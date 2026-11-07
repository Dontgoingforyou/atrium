from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import InvoiceStatus, InvoiceType


class ContractShort(BaseModel):
    id: uuid.UUID
    title: str

    model_config = {"from_attributes": True}


class PortalInvoiceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    contract_id: uuid.UUID | None = None
    invoice_type: InvoiceType = Field(default=InvoiceType.INVOICE)
    amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str = Field(default="RUB", max_length=10)
    issue_date: date | None = None
    due_date: date | None = None
    status: InvoiceStatus = Field(default=InvoiceStatus.DRAFT)


class PortalInvoiceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    contract_id: uuid.UUID | None = None
    invoice_type: InvoiceType | None = None
    amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str | None = Field(default=None, max_length=10)
    issue_date: date | None = None
    due_date: date | None = None
    status: InvoiceStatus | None = None


class PortalInvoiceRead(BaseModel):
    id: uuid.UUID
    title: str
    contract_id: uuid.UUID | None
    contract: ContractShort | None = None
    invoice_type: str
    amount: Decimal | None
    currency: str
    issue_date: date | None
    due_date: date | None
    status: str
    author_sub: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
