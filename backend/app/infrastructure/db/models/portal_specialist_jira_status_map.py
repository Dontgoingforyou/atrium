"""Маппинг id статуса Jira → колонка воронки (все статусы колонки доски, не только primary)."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class PortalSpecialistJiraStatusMap(Base):
    __tablename__ = "portal_specialist_jira_status_map"

    jira_status_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    column_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_specialist_column.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
