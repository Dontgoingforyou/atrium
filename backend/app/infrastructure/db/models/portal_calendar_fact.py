"""Уже применённый факт календаря. Повтор той же доставки уведомление не создаёт."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class PortalCalendarFact(Base):
    __tablename__ = "portal_calendar_fact"

    fact_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    consumed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
