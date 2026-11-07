from __future__ import annotations

from pydantic import BaseModel, Field


class PagedResponse[T](BaseModel):
    """Стандартный постраничный ответ API."""

    items: list[T]
    total: int = Field(description="Общее число записей (без пагинации)")
    skip: int = Field(description="Смещение текущей страницы")
    limit: int = Field(description="Размер страницы")
