from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import (
    ContractStatus,
    ContractType,
    CounterpartyType,
    InvoiceStatus,
    InvoiceType,
    PaymentCategory,
    ProcurementStatus,
)
from app.infrastructure.db.base import Base


def _enum_values(enum_cls: type) -> list[str]:
    """Возвращает список значений (value) для SQLAlchemy Enum.

    По умолчанию SQLAlchemy использует имена (name) членов enum,
    но PostgreSQL-тип создан с lowercase-значениями (value).
    values_callable=_enum_values исправляет это несоответствие.
    """
    return [e.value for e in enum_cls]  # type: ignore[attr-defined]


if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_document import PortalDocument
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalCounterparty(Base):
    """Контрагент: внешняя организация для договоров и закупок."""

    __tablename__ = "portal_counterparty"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    inn: Mapped[str | None] = mapped_column(String(20), nullable=True, unique=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    counterparty_type: Mapped[str] = mapped_column(
        Enum(CounterpartyType, name="counterparty_type_enum", values_callable=_enum_values),
        nullable=False,
        default=CounterpartyType.VENDOR.value,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    author_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    contracts: Mapped[list[PortalContract]] = relationship(
        "PortalContract", back_populates="counterparty", lazy="noload"
    )
    author_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalCounterparty.author_sub == PortalUserProfile.sub",
        foreign_keys="[PortalCounterparty.author_sub]",
        lazy="noload",
    )

    def __str__(self) -> str:
        return self.name


class PortalContract(Base):
    """Договор с контрагентом."""

    __tablename__ = "portal_contract"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    contract_type: Mapped[str] = mapped_column(
        Enum(ContractType, name="contract_type_enum", values_callable=_enum_values),
        nullable=False,
        default=ContractType.ACTIVE.value,
        index=True,
    )
    counterparty_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_counterparty.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="RUB")
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(ContractStatus, name="contract_status_enum", values_callable=_enum_values),
        nullable=False,
        default=ContractStatus.DRAFT.value,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    owner_sub: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    counterparty: Mapped[PortalCounterparty | None] = relationship(
        "PortalCounterparty", back_populates="contracts", lazy="select"
    )
    document: Mapped[PortalDocument | None] = relationship("PortalDocument", foreign_keys=[document_id], lazy="noload")
    invoices: Mapped[list[PortalInvoice]] = relationship("PortalInvoice", back_populates="contract", lazy="noload")
    author_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalContract.author_sub == PortalUserProfile.sub",
        foreign_keys="[PortalContract.author_sub]",
        lazy="noload",
    )
    owner_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalContract.owner_sub == PortalUserProfile.sub",
        foreign_keys="[PortalContract.owner_sub]",
        lazy="noload",
    )

    def __str__(self) -> str:
        return self.title


class PortalInvoice(Base):
    """Счёт на оплату или акт выполненных работ."""

    __tablename__ = "portal_invoice"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_contract.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    invoice_type: Mapped[str] = mapped_column(
        Enum(InvoiceType, name="invoice_type_enum", values_callable=_enum_values),
        nullable=False,
        default=InvoiceType.INVOICE.value,
        index=True,
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="RUB")
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        Enum(InvoiceStatus, name="invoice_status_enum", values_callable=_enum_values),
        nullable=False,
        default=InvoiceStatus.DRAFT.value,
        index=True,
    )
    author_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    contract: Mapped[PortalContract | None] = relationship("PortalContract", back_populates="invoices", lazy="select")
    payments: Mapped[list[PortalPayment]] = relationship("PortalPayment", back_populates="invoice", lazy="noload")
    author_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalInvoice.author_sub == PortalUserProfile.sub",
        foreign_keys="[PortalInvoice.author_sub]",
        lazy="noload",
    )

    def __str__(self) -> str:
        return self.title


class PortalPayment(Base):
    """Платёж по счёту."""

    __tablename__ = "portal_payment"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_invoice.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=18, scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="RUB")
    paid_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_category: Mapped[str] = mapped_column(
        Enum(PaymentCategory, name="payment_category_enum", values_callable=_enum_values),
        nullable=False,
        default=PaymentCategory.CONTRACT.value,
        index=True,
    )
    author_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    invoice: Mapped[PortalInvoice | None] = relationship("PortalInvoice", back_populates="payments", lazy="select")
    author_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalPayment.author_sub == PortalUserProfile.sub",
        foreign_keys="[PortalPayment.author_sub]",
        lazy="noload",
    )

    def __str__(self) -> str:
        return f"{self.amount} {self.currency} ({self.paid_at})"


class PortalProcurementRequest(Base):
    """Закупочная заявка."""

    __tablename__ = "portal_procurement_request"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(ProcurementStatus, name="procurement_status_enum", values_callable=_enum_values),
        nullable=False,
        default=ProcurementStatus.DRAFT.value,
        index=True,
    )
    counterparty_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_counterparty.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    amount: Mapped[Decimal | None] = mapped_column(Numeric(precision=18, scale=2), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="RUB")
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    counterparty: Mapped[PortalCounterparty | None] = relationship(
        "PortalCounterparty", foreign_keys=[counterparty_id], lazy="noload"
    )
    document: Mapped[PortalDocument | None] = relationship("PortalDocument", foreign_keys=[document_id], lazy="noload")
    author_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalProcurementRequest.author_sub == PortalUserProfile.sub",
        foreign_keys="[PortalProcurementRequest.author_sub]",
        lazy="noload",
    )

    def __str__(self) -> str:
        return self.title
