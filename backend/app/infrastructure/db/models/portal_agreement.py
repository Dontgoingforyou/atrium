from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import AgreementStatus
from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_chat import PortalChatMessage
    from app.infrastructure.db.models.portal_document import PortalDocument
    from app.infrastructure.db.models.portal_task import PortalTask
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalAgreement(Base):
    __tablename__ = "portal_agreement"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(AgreementStatus, native_enum=False, length=32),
        nullable=False,
        server_default=AgreementStatus.DRAFT,
        index=True,
    )
    source_message_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_chat_message.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_document.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_task.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_by_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    source_message: Mapped[PortalChatMessage | None] = relationship(foreign_keys=[source_message_id], lazy="select")
    document: Mapped[PortalDocument | None] = relationship(foreign_keys=[document_id], lazy="select")
    task: Mapped[PortalTask | None] = relationship(foreign_keys=[task_id], lazy="select")
    created_by_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalAgreement.created_by_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
        overlaps="created_by_user",
    )
    created_by_user: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="foreign(PortalAgreement.created_by_sub) == PortalUserProfile.sub",
        lazy="noload",
        overlaps="created_by_profile",
    )

    @property
    def source_chat_id(self) -> uuid.UUID | None:
        """Идентификатор чата исходного сообщения (для API без ручного UUID)."""
        if self.source_message_id is None:
            return None
        msg = self.source_message
        return msg.chat_id if msg is not None else None

    def __str__(self) -> str:
        return f"Договорённость от {str(self.created_at)[:10]}"
