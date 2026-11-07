from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import ProcurementStatus


class PortalProcurementRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    counterparty_id: uuid.UUID | None = None
    amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str = Field(default="RUB", max_length=10)
    document_id: uuid.UUID | None = None
    status: ProcurementStatus = Field(default=ProcurementStatus.DRAFT)


class PortalProcurementRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    counterparty_id: uuid.UUID | None = None
    amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    currency: str | None = Field(default=None, max_length=10)
    document_id: uuid.UUID | None = None
    status: ProcurementStatus | None = None


class PortalCounterpartyShort(BaseModel):
    id: uuid.UUID
    name: str

    model_config = {"from_attributes": True}


class PortalProcurementRequestRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    status: str
    counterparty_id: uuid.UUID | None
    counterparty: PortalCounterpartyShort | None = None
    amount: Decimal | None
    currency: str
    document_id: uuid.UUID | None
    author_sub: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProcurementSummaryRead(BaseModel):
    """Агрегат по закупочным заявкам."""

    total: int = Field(description="Всего заявок в выборке")
    by_status: dict[str, int] = Field(description="Количество заявок по каждому статусу")
    total_budget: Decimal = Field(description="Суммарный бюджет по всем заявкам")
