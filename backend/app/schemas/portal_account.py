from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PortalAccountPreferencesRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notify_document_trash: bool = Field(
        description="Уведомлять о перемещении документов в корзину (только для администраторов)"
    )
    guided_tour_completed: bool = Field(description="Пользователь завершил или пропустил guided tour (онбординг UI)")


class PortalAccountPreferencesUpdate(BaseModel):
    notify_document_trash: bool | None = None
    guided_tour_completed: bool | None = None
