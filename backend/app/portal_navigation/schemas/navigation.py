from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class NavDocumentBrief(BaseModel):
    """Краткое представление документа для навигационного дерева."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    icon_emoji: str | None = None
    children: list[NavDocumentBrief] = Field(default_factory=list)
    shortcuts: list[NavDocumentBrief] = Field(
        default_factory=list,
        description="Ярлыки из documentLink в body (без смены parent_document_id).",
    )


NavDocumentBrief.model_rebuild()


class PortalNavNodeTree(BaseModel):
    """Узел дерева левого меню."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    title: str
    sort_order: int = Field(..., description="Порядок сортировки среди соседей")
    document_count_subtree: int = Field(
        ...,
        ge=0,
        description="Число верхнеуровневых документов под этим узлом (вложенные — в children документов).",
    )
    documents: list[NavDocumentBrief] = Field(
        default_factory=list,
        description="Верхнеуровневые документы этого узла.",
    )
    children: list[PortalNavNodeTree] = Field(default_factory=list)
