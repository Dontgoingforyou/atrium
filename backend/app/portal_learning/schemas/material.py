from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import LearningMaterialStatus, LearningMaterialType


class LearningMaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: uuid.UUID
    title: str
    body: str | None
    material_type: str
    status: str
    idp_groups: list[str]
    created_by_sub: str
    version: int = Field(description="Версия для optimistic locking (CAS)")
    created_at: datetime
    updated_at: datetime


class LearningMaterialCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    body: str | None = None
    material_type: LearningMaterialType = LearningMaterialType.ARTICLE
    status: LearningMaterialStatus = LearningMaterialStatus.DRAFT
    idp_groups: list[str] = Field(default_factory=list, description="Группы доступа; пусто = для всех")


class LearningMaterialUpdate(BaseModel):
    expected_version: int = Field(..., ge=1, description="Версия материала, прочитанная клиентом (CAS)")
    title: str | None = Field(default=None, min_length=1, max_length=512)
    body: str | None = None
    material_type: LearningMaterialType | None = None
    status: LearningMaterialStatus | None = None
    idp_groups: list[str] | None = None
