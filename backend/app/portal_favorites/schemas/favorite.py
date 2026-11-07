from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import FavoriteTargetType


class PortalFavoriteCreate(BaseModel):
    """Тело запроса на добавление в избранное."""

    target_type: FavoriteTargetType = Field(description="Тип объекта; поддерживается document")
    target_id: uuid.UUID = Field(description="Идентификатор документа")


class PortalFavoriteRead(BaseModel):
    """Элемент списка избранного с подписью для UI/API-клиентов."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_type: FavoriteTargetType
    target_id: uuid.UUID
    created_at: datetime
    title: str = Field(description="Заголовок документа для отображения в списке")
