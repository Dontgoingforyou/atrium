from __future__ import annotations

from pydantic import BaseModel, Field


class PortalPushKeys(BaseModel):
    p256dh: str = Field(min_length=1)
    auth: str = Field(min_length=1)


class PortalPushSubscribe(BaseModel):
    endpoint: str = Field(min_length=8, max_length=4096)
    keys: PortalPushKeys


class PortalPushUnsubscribe(BaseModel):
    endpoint: str = Field(min_length=8, max_length=4096)


class PortalPushVapidPublicRead(BaseModel):
    public_key: str = Field(description="Публичный ключ VAPID (base64url) для applicationServerKey")
