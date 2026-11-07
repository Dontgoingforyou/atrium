"""Вложения rich-text (изображения в описании задачи или теле документа)."""

from __future__ import annotations

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import CheckConstraint, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class PortalRichMedia(Base):
    __tablename__ = "portal_rich_media"
    __table_args__ = (
        CheckConstraint(
            "(task_id IS NOT NULL AND document_id IS NULL AND specialist_sub IS NULL) OR "
            "(task_id IS NULL AND document_id IS NOT NULL AND specialist_sub IS NULL) OR "
            "(task_id IS NULL AND document_id IS NULL AND specialist_sub IS NOT NULL)",
            name="ck_portal_rich_media_single_parent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    storage_key: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    original_filename: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    file_size: Mapped[int] = mapped_column(sa.BigInteger, nullable=False)
    uploader_sub: Mapped[str] = mapped_column(sa.String(128), nullable=False, index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("portal_task.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("portal_document.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    specialist_sub: Mapped[str | None] = mapped_column(
        sa.String(255),
        ForeignKey("portal_user_profile.sub", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
