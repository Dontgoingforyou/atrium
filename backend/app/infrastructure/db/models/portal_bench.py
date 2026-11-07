"""Снимки дашборда бенч по годам и состояние фоновой синхронизации."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.infrastructure.db.base import Base


class PortalBenchYearSnapshot(Base):
    """Снимок воронки АУ за календарный год (JSON-строки ingest)."""

    __tablename__ = "portal_bench_year_snapshot"
    __table_args__ = (Index("ix_portal_bench_year_snapshot_frozen", "frozen"),)

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    frozen: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    records: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __str__(self) -> str:
        return f"bench {self.year} ({self.source})"


class PortalBenchSyncState(Base):
    """Единственная строка состояния sync Google Таблицы (id=1)."""

    __tablename__ = "portal_bench_sync_state"
    __table_args__ = (CheckConstraint("id = 1", name="ck_portal_bench_sync_state_singleton"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __str__(self) -> str:
        return f"bench sync state {self.id}"
