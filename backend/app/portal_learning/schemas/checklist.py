from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    checklist_id: uuid.UUID
    order_index: int
    text: str


class ChecklistRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: str | None
    idp_group: str
    version: int = Field(description="Версия для optimistic locking (CAS)")
    created_at: datetime
    updated_at: datetime
    items: list[ChecklistItemRead] = []


class ChecklistCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    idp_group: str = Field(default="", max_length=128, description="Имя группы Keycloak; пусто = для всех")
    items: list[str] = Field(default_factory=list, description="Тексты пунктов чек-листа")


class ChecklistUpdate(BaseModel):
    expected_version: int = Field(..., ge=1, description="Версия чек-листа, прочитанная клиентом (CAS)")
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    idp_group: str | None = Field(default=None, max_length=128)
    items: list[str] | None = Field(
        default=None,
        description="Полная замена списка пунктов; сбрасывает прогресс всех пользователей по этому чек-листу.",
    )


class UserChecklistItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_checklist_id: uuid.UUID
    item_id: uuid.UUID
    is_done: bool
    done_at: datetime | None


class UserChecklistProgressRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_sub: str
    checklist_id: uuid.UUID
    status: str
    started_at: datetime
    completed_at: datetime | None
    item_marks: list[UserChecklistItemRead] = []
    checklist: ChecklistRead | None = None


class MarkItemBody(BaseModel):
    is_done: bool
