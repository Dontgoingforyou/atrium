from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth_constants import IDP_KNOWN_PORTAL_GROUPS
from app.core.enums import LearningMaterialStatus
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.optimistic_lock import compare_and_swap_row
from app.core.utils import now_utc as _now_utc
from app.infrastructure.db.models.portal_learning import (
    PortalLearningMaterial,
    PortalLearningMaterialIdpGroup,
)
from app.portal_learning.schemas.material import LearningMaterialCreate, LearningMaterialUpdate
from app.schemas.auth import UserPublic

_MATERIAL_CAS_CONFLICT = "Материал изменён другим пользователем"
_MATERIAL_ROW_FIELDS = frozenset({"title", "body", "material_type", "status"})


def _unique_known_idp_groups(values: list[str]) -> list[str]:
    """Сохраняем порядок, только известные группы Keycloak (см. auth_constants)."""
    out: list[str] = []
    for v in values:
        s = (v or "").strip()
        if s and s in IDP_KNOWN_PORTAL_GROUPS and s not in out:
            out.append(s)
    return out


def _is_material_visible(material: PortalLearningMaterial, user: UserPublic) -> bool:
    """Черновик — только admin; архив — никому кроме admin; без групп — всем; иначе — пересечение idp."""
    if user.is_portal_admin:
        return True
    if material.status != LearningMaterialStatus.ACTIVE:
        return False
    links = getattr(material, "idp_group_rows", None) or []
    if not links:
        return True
    need = {x.idp_group for x in links}
    return bool(need & set(user.idp_groups))


def _set_material_idp_groups(
    mat: PortalLearningMaterial,
    groups: list[str],
) -> None:
    wanted = _unique_known_idp_groups(groups)
    mat.idp_group_rows = [PortalLearningMaterialIdpGroup(idp_group=g) for g in wanted]


async def list_materials(
    session: AsyncSession,
    user: UserPublic,
    *,
    material_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PortalLearningMaterial]:
    """Список материалов, видимых пользователю."""
    stmt = (
        select(PortalLearningMaterial)
        .options(selectinload(PortalLearningMaterial.idp_group_rows))
        .order_by(PortalLearningMaterial.created_at.desc())
    )
    if not user.is_portal_admin:
        stmt = stmt.where(PortalLearningMaterial.status == LearningMaterialStatus.ACTIVE)
    if material_type is not None:
        stmt = stmt.where(PortalLearningMaterial.material_type == material_type)
    if status is not None and user.is_portal_admin:
        stmt = stmt.where(PortalLearningMaterial.status == status)
    rows = list((await session.scalars(stmt)).all())
    visible = [r for r in rows if _is_material_visible(r, user)]
    return visible[offset : offset + limit]


async def get_material(
    session: AsyncSession,
    user: UserPublic,
    material_id: uuid.UUID,
) -> PortalLearningMaterial:
    stmt = (
        select(PortalLearningMaterial)
        .where(PortalLearningMaterial.id == material_id)
        .options(selectinload(PortalLearningMaterial.idp_group_rows))
    )
    row = (await session.scalars(stmt)).first()
    if row is None or not _is_material_visible(row, user):
        raise NotFoundError("Материал не найден")
    return row


async def create_material(
    session: AsyncSession,
    user: UserPublic,
    data: LearningMaterialCreate,
) -> PortalLearningMaterial:
    if not user.is_portal_admin:
        raise ForbiddenError("Создание материалов доступно только администраторам")
    row = PortalLearningMaterial(
        title=data.title,
        body=data.body,
        material_type=data.material_type.value,
        status=data.status.value,
        created_by_sub=user.sub,
    )
    if data.idp_groups:
        _set_material_idp_groups(row, data.idp_groups)
    session.add(row)
    await session.commit()
    await session.refresh(row, attribute_names=["idp_group_rows"])
    return row


async def update_material(
    session: AsyncSession,
    user: UserPublic,
    material_id: uuid.UUID,
    data: LearningMaterialUpdate,
) -> PortalLearningMaterial:
    if not user.is_portal_admin:
        raise ForbiddenError("Редактирование материалов доступно только администраторам")
    stmt = (
        select(PortalLearningMaterial)
        .where(PortalLearningMaterial.id == material_id)
        .options(selectinload(PortalLearningMaterial.idp_group_rows))
    )
    row = (await session.scalars(stmt)).first()
    if row is None:
        raise NotFoundError("Материал не найден")
    patch = data.model_dump(exclude_unset=True)
    patch.pop("expected_version", None)
    has_idp = "idp_groups" in patch
    idp_groups = patch.pop("idp_groups", None) if has_idp else None
    has_row_changes = bool(_MATERIAL_ROW_FIELDS.intersection(patch))
    if not has_row_changes and not has_idp:
        return row

    values: dict[str, Any] = {"updated_at": _now_utc()}
    if data.title is not None:
        values["title"] = data.title
    if "body" in patch:
        values["body"] = data.body
    if data.material_type is not None:
        values["material_type"] = data.material_type.value
    if data.status is not None:
        values["status"] = data.status.value

    new_version = await compare_and_swap_row(
        session,
        PortalLearningMaterial,
        entity_id=material_id,
        expected_version=data.expected_version,
        values=values,
        conflict_message=_MATERIAL_CAS_CONFLICT,
    )
    await session.refresh(row)
    row.version = new_version

    if has_idp:
        _set_material_idp_groups(row, idp_groups or [])

    await session.commit()
    await session.refresh(row, attribute_names=["idp_group_rows"])
    return row


async def delete_material(session: AsyncSession, user: UserPublic, material_id: uuid.UUID) -> None:
    if not user.is_portal_admin:
        raise ForbiddenError("Удаление материалов доступно только администраторам")
    stmt = (
        select(PortalLearningMaterial)
        .where(PortalLearningMaterial.id == material_id)
        .options(selectinload(PortalLearningMaterial.idp_group_rows))
    )
    row = (await session.scalars(stmt)).first()
    if row is None:
        raise NotFoundError("Материал не найден")
    await session.delete(row)
    await session.commit()
