"""Fulltext-поиск специалистов.

RBAC:
- portal_admin — видит всех специалистов (у кого есть хотя бы одна связь manager-specialist).
- менеджер (IDP_GROUP_MANAGER) — только своих специалистов (по portal_manager_specialist).
- остальные — доступ запрещён.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.text_search import escape_ilike_pattern
from app.portal_specialists.services.board_shared import require_manager_or_admin
from app.schemas.auth import UserPublic


@dataclass
class SpecialistSearchRow:
    sub: str
    full_name: str | None
    email: str | None
    created_at: datetime


async def search_specialists_for_user(
    db: AsyncSession,
    user: UserPublic,
    q: str,
    *,
    status_ids: list[uuid.UUID] | None = None,  # legacy ms.status_id, не profile.direction
    skip: int = 0,
    limit: int = 100,
) -> list[SpecialistSearchRow]:
    """Поиск специалистов по имени и email с учётом RBAC."""
    require_manager_or_admin(user, "Поиск специалистов доступен только менеджерам и администраторам")

    pattern = f"%{escape_ilike_pattern(q.lower())}%"
    status_filter = ""
    if status_ids:
        status_filter = " AND ms.status_id = ANY(CAST(:status_ids AS uuid[]))"

    name_match = "lower(up.full_name) LIKE :pat ESCAPE '\\' OR lower(up.email) LIKE :pat ESCAPE '\\'"
    if user.is_portal_admin:
        if status_ids:
            sql = sa.text(
                "SELECT DISTINCT up.sub, up.full_name, up.email, up.updated_at "
                "FROM portal_user_profile up "
                "JOIN portal_manager_specialist ms ON ms.specialist_sub = up.sub "
                f"WHERE ({name_match})" + status_filter + " ORDER BY up.full_name "
                "LIMIT :limit OFFSET :skip"
            )
        else:
            sql = sa.text(
                "SELECT DISTINCT up.sub, up.full_name, up.email, up.updated_at "
                "FROM portal_user_profile up "
                "WHERE EXISTS ("
                "  SELECT 1 FROM portal_manager_specialist ms "
                "  WHERE ms.specialist_sub = up.sub"
                ") "
                f"AND ({name_match}) "
                "ORDER BY up.full_name "
                "LIMIT :limit OFFSET :skip"
            )
        params: dict[str, object] = {"pat": pattern, "limit": limit, "skip": skip}
    else:
        sql = sa.text(
            "SELECT DISTINCT up.sub, up.full_name, up.email, up.updated_at "
            "FROM portal_user_profile up "
            "JOIN portal_manager_specialist ms ON ms.specialist_sub = up.sub "
            "WHERE ms.manager_sub = :manager_sub "
            f"AND ({name_match})" + status_filter + " ORDER BY up.full_name "
            "LIMIT :limit OFFSET :skip"
        )
        params = {"manager_sub": user.sub, "pat": pattern, "limit": limit, "skip": skip}

    if status_ids:
        params["status_ids"] = [str(s) for s in status_ids]

    rows = (await db.execute(sql, params)).fetchall()
    return [SpecialistSearchRow(sub=r.sub, full_name=r.full_name, email=r.email, created_at=r.updated_at) for r in rows]
