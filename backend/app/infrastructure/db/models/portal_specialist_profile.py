from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


class PortalSpecialistProfile(Base):
    """Расширенный профиль специалиста (один-к-одному с portal_user_profile).

    Создаётся лениво при первом обращении (get_or_create).
    Редактировать может portal_admin или менеджер, закрепивший этого специалиста.
    """

    __tablename__ = "portal_specialist_profile"

    specialist_sub: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("portal_user_profile.sub", ondelete="CASCADE"),
        primary_key=True,
    )
    birthdate: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telegram: Mapped[str | None] = mapped_column(String(100), nullable=True)
    direction: Mapped[str | None] = mapped_column(String(255), nullable=True)
    jira_issue_key: Mapped[str | None] = mapped_column(String(32), nullable=True, unique=True, index=True)
    jira_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    jira_fields: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")

    user_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalSpecialistProfile.specialist_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )

    def __str__(self) -> str:
        prof = self.__dict__.get("user_profile")
        if prof is not None:
            name = prof.full_name or prof.email or prof.username
            if name:
                return str(name)
        sub = self.specialist_sub
        return sub[:20] + "…" if len(sub) > 20 else sub
