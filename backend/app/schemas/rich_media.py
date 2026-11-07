"""Схемы API для изображений rich-text."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RichMediaRead(BaseModel):
    id: uuid.UUID
    content_type: str
    file_size: int
    original_filename: str
    file_path: str = Field(description="Путь API без хоста, например /api/v1/portal/rich-media/{id}/file")
    download_url: str = Field(description="Временный presigned URL для отображения")
    created_at: datetime
