from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import FavoriteTargetType
from app.infrastructure.db.base import Base


class PortalFavorite(Base):
    """Избранное: связь пользователь (sub из IdP) → объект портала."""

    __tablename__ = "portal_favorite"
    __table_args__ = (UniqueConstraint("user_sub", "target_type", "target_id", name="uq_portal_favorite_user_target"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(
        Enum(FavoriteTargetType, native_enum=False, length=32),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
