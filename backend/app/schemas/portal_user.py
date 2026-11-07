from __future__ import annotations

from datetime import datetime

from app.core.enums import PresenceState
from pydantic import BaseModel, ConfigDict, Field


class PortalUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sub: str
    display_name: str | None = None
    email: str | None = None
    username: str | None = None
    presence: PresenceState = Field(
        default="offline",
        description="Статус присутствия (Redis; без Redis — всегда offline)",
    )
    avatar_url: str | None = None
    last_seen_at: datetime | None = Field(
        default=None,
        description="Оценка последней активности в приложении (PostgreSQL; для offline)",
    )
    avatar_focal_x: float | None = Field(
        default=None,
        description="Горизонталь фокуса кадра аватара 0–1 (центр видимой области)",
    )
    avatar_focal_y: float | None = Field(
        default=None,
        description="Вертикаль фокуса кадра аватара 0–1",
    )


class PortalUserPresenceRead(BaseModel):
    """Только присутствие для объединения с кэшем без повторной генерации presigned URL аватаров."""

    sub: str
    presence: PresenceState = Field(
        default="offline",
        description="Статус присутствия (Redis; без Redis — всегда offline)",
    )
    last_seen_at: datetime | None = Field(
        default=None,
        description="Метка последней активности из Redis",
    )


class PortalPresenceUpdate(BaseModel):
    """Heartbeat присутствия: вкладка видима и была ли недавно активность пользователя."""

    visible: bool = Field(description="Вкладка приложения на переднем плане")
    active: bool = Field(
        default=False,
        description="Была пользовательская активность (ввод, клик) недавно",
    )


class PresenceBeaconBody(BaseModel):
    """Тело beacon-запроса присутствия (sendBeacon при закрытии вкладки).

    JWT передаётся в теле, так как sendBeacon не поддерживает заголовок Authorization.
    """

    access_token: str = Field(max_length=8192)
    visible: bool
    active: bool


class AvatarUploadRead(BaseModel):
    """Результат загрузки аватара текущего пользователя."""

    avatar_url: str | None = Field(default=None, description="Signed proxy URL фото из Effective Admin")
    avatar_focal_x: float | None = Field(
        default=None,
        description="Устарело: фокус кадра больше не используется для user-аватара",
    )
    avatar_focal_y: float | None = Field(
        default=None,
        description="Устарело: фокус кадра больше не используется для user-аватара",
    )
