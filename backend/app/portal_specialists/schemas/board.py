"""Схемы Pydantic для доски воронки специалистов."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Колонки воронки
# ---------------------------------------------------------------------------


class SpecialistColumnRead(BaseModel):
    id: uuid.UUID
    key: str
    title: str
    color: str
    position: int

    model_config = {"from_attributes": True}


class SpecialistColumnCreate(BaseModel):
    key: str = Field(max_length=100, description="Уникальный ключ колонки (латиница, без пробелов)")
    title: str = Field(max_length=200, description="Название колонки")
    color: str = Field(default="#888888", max_length=30, description="Цвет колонки (hex)")
    position: int = Field(default=0, ge=0, description="Порядковый номер")


class SpecialistColumnUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    color: str | None = Field(default=None, max_length=30)
    position: int | None = Field(default=None, ge=0)


class SpecialistBoardPrefRead(BaseModel):
    column_order: list[str] = Field(default_factory=list)
    hidden_column_keys: list[str] = Field(default_factory=list)


class SpecialistBoardPrefWrite(BaseModel):
    column_order: list[str] = Field(default_factory=list)
    hidden_column_keys: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Статусы специалистов
# ---------------------------------------------------------------------------


class SpecialistStatusRead(BaseModel):
    id: uuid.UUID
    title: str
    color: str

    model_config = {"from_attributes": True}


class SpecialistStatusCreate(BaseModel):
    title: str = Field(max_length=100, description="Название статуса")
    color: str = Field(default="#888888", max_length=30, description="Цвет статуса (hex)")


class SpecialistStatusUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=100)
    color: str | None = Field(default=None, max_length=30)


# ---------------------------------------------------------------------------
# Записи доски
# ---------------------------------------------------------------------------


class ManagerSpecialistEntryRead(BaseModel):
    """Специалист на доске воронки менеджера, обогащённый профилями и статусом."""

    id: uuid.UUID
    specialist_sub: str
    display_name: str | None
    email: str | None
    avatar_url: str | None
    column_key: str
    position: int
    version: int
    manager_sub: str
    manager_display_name: str | None
    status_id: uuid.UUID | None
    status_title: str | None
    status_color: str | None
    created_at: datetime


class ManagerSpecialistAdd(BaseModel):
    specialist_sub: str = Field(description="Идентификатор специалиста")
    column_key: str = Field(default="new", max_length=100, description="Ключ колонки воронки")


class ManagerSpecialistPatch(BaseModel):
    """Патч записи на доске (колонка и позиция). Legacy ``status_id`` в теле не принимается."""

    expected_version: int = Field(..., ge=1, description="Версия записи, прочитанная клиентом (CAS)")
    column_key: str | None = Field(default=None, max_length=100)
    position: int | None = Field(default=None, ge=0)


class ManagerSpecialistReorder(BaseModel):
    """Перемещение записи доски относительно соседней записи того же менеджера."""

    entry_id: uuid.UUID
    column_key: str = Field(min_length=1, max_length=100)
    after_entry_id: uuid.UUID | None = None
    before_entry_id: uuid.UUID | None = None


class ManagerReassignBody(BaseModel):
    """Смена менеджера у закрепления специалиста (только администратор)."""

    from_manager_sub: str = Field(description="Текущий sub менеджера")
    to_manager_sub: str = Field(description="Новый sub менеджера")


class SpecialistManagerRef(BaseModel):
    """Менеджер, за которым закреплён специалист (для drawer SPA и эндпоинта by-specialist)."""

    manager_sub: str
    manager_display_name: str | None
    manager_avatar_url: str | None = None
    manager_avatar_focal_x: float | None = None
    manager_avatar_focal_y: float | None = None
    column_key: str
    status_id: uuid.UUID | None
    status_title: str | None
    status_color: str | None
    created_at: datetime
