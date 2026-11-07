"""Optimistic locking (compare-and-swap) для редактируемых portal-сущностей."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.core.exceptions import ConflictError


async def compare_and_swap_row(
    session: AsyncSession,
    model: type[DeclarativeBase],
    *,
    entity_id: UUID | str,
    expected_version: int,
    values: dict[str, Any],
    conflict_message: str,
    id_column_name: str = "id",
) -> int:
    """Атомарно применить ``values`` и увеличить ``version``.

    ``UPDATE … SET …, version = expected + 1 WHERE <pk> = :id AND version = :expected``.
    При ``rowcount != 1`` — ``ConflictError`` (HTTP 409, ``code=conflict``).
    Возвращает новую версию.

    ``id_column_name`` — имя PK-колонки (по умолчанию ``id``; для профиля специалиста — ``specialist_sub``).
    """
    if "version" in values:
        raise ValueError("version задаётся хелпером CAS, не передавать в values")
    table = model.__table__
    id_col = table.c[id_column_name]
    version_col = table.c.version
    new_version = expected_version + 1
    stmt = (
        update(model).where(id_col == entity_id, version_col == expected_version).values(**values, version=new_version)
    )
    result = cast(CursorResult[Any], await session.execute(stmt))
    if result.rowcount != 1:
        raise ConflictError(conflict_message)
    return new_version
