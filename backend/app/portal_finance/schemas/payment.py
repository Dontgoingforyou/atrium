from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.core.enums import PaymentCategory


class InvoiceShort(BaseModel):
    id: uuid.UUID
    title: str

    model_config = {"from_attributes": True}


class PortalPaymentCreate(BaseModel):
    invoice_id: uuid.UUID | None = None
    amount: Decimal = Field(gt=0, decimal_places=2)
    currency: str = Field(default="RUB", max_length=10)
    paid_at: date | None = None
    note: str | None = Field(default=None, max_length=4000)
    payment_category: PaymentCategory = Field(default=PaymentCategory.CONTRACT)


class PortalPaymentRead(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID | None
    invoice: InvoiceShort | None = None
    amount: Decimal
    currency: str
    paid_at: date | None
    note: str | None
    payment_category: str
    author_sub: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FinanceSummaryRead(BaseModel):
    """Агрегат по финансовому срезу."""

    contracts_total: int = Field(description="Всего договоров в выборке")
    contracts_active: int
    invoices_total: int
    invoices_paid: int
    invoices_overdue: int
    payments_total_amount: Decimal = Field(description="Сумма всех платежей в выборке")
    payments_count: int
