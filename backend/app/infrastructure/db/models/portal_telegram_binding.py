from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class PortalTelegramBinding(Base):
    __tablename__ = "portal_telegram_binding"

    user_sub: Mapped[str] = mapped_column(String(255), primary_key=True)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger(), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
