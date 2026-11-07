from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BindInitResponse(BaseModel):
    code: str = Field(description="Одноразовый код для /start в боте")
    bot_url: str = Field(description="Deep link для открытия бота с кодом")


class BindStatusResponse(BaseModel):
    bound: bool
    created_at: datetime | None = None
