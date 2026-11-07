from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import TypeDecorator, TypeEngine

from app.infrastructure.db.base import Base


class _VectorCompat(TypeDecorator[list[float]]):
    """Тип vector(1536) для PostgreSQL; TEXT (JSON) для SQLite (тесты)."""

    impl = Text
    cache_ok = True

    def __init__(self, dim: int = 1536) -> None:
        super().__init__()
        self._dim = dim

    def load_dialect_impl(self, dialect: Any) -> TypeEngine[Any]:
        if dialect.name == "postgresql":
            from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped, unused-ignore]

            result: TypeEngine[Any] = dialect.type_descriptor(Vector(self._dim))
            return result
        result2: TypeEngine[Any] = dialect.type_descriptor(Text())
        return result2

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name != "postgresql":
            return json.dumps(value) if isinstance(value, list) else value
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if dialect.name != "postgresql" and isinstance(value, str):
            return json.loads(value)
        return value


class PortalEmbedding(Base):
    """Векторный эмбеддинг любой сущности портала для семантического поиска."""

    __tablename__ = "portal_embedding"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_portal_embedding_type_id"),
        Index("ix_portal_embedding_entity_type", "entity_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Тип сущности: document, task, chat_message, agreement",
    )
    entity_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Строковое представление ID сущности (UUID или int)",
    )
    text_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Текст, который был векторизован",
    )
    embedding: Mapped[Any] = mapped_column(
        _VectorCompat(1536),
        nullable=False,
        doc="Вектор эмбеддинга размерности 1536 (text-embedding-3-small)",
    )
    meta: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        server_default="{}",
        doc="Дополнительные метаданные для фильтрации (author_sub, status и т.п.)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PortalEmbedding {self.entity_type}#{self.entity_id}>"
