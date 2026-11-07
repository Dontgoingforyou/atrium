from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class PortalUserProfile(Base):
    """Профиль пользователя портала, сохраняемый при каждом логине.

    Источник данных — Keycloak userinfo. Обновляется автоматически
    при каждом успешном обращении к API (cache miss по токену).
    is_portal_admin — кэш признака из IdP (обновляется при build_user_public).
    portal_chat_allowed — кэш: чаты портала разрешены (False для students без админа).
    """

    __tablename__ = "portal_user_profile"

    sub: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_portal_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Кэш «timesheet-only / группа students» для восстановления IdP-групп в уведомлениях, не роль разработчика.
    is_developer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    # Кэш основного отдела SSO (claim gid_number); отдел АУ = SSO_GID_OUTSTAFF.
    gid_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    portal_chat_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    notify_document_trash: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    guided_tour_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __str__(self) -> str:
        return self.full_name or self.email or self.username or self.sub
