from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class PortalSpecialistLink(Base):
    """Ссылка, добавленная менеджером или администратором к профилю специалиста."""

    __tablename__ = "portal_specialist_link"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    specialist_sub: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("portal_user_profile.sub", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    created_by_sub: Mapped[str | None] = mapped_column(
        String(255),
        ForeignKey("portal_user_profile.sub", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
