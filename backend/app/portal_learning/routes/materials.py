from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.core.portal_search_constants import PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL
from app.infrastructure.db.models.portal_learning import PortalLearningMaterial
from app.portal_learning.schemas.material import (
    LearningMaterialCreate,
    LearningMaterialRead,
    LearningMaterialUpdate,
)
from app.portal_learning.services import material as svc
from app.portal_search.services import embedding as emb_svc
from app.portal_search.services.entity_text import learning_material_meta, learning_material_to_text

router = APIRouter(tags=["Обучение · Материалы"])


def _material_to_read(row: PortalLearningMaterial) -> LearningMaterialRead:
    """Маппинг ORM → API-схема; `idp_groups` — плоский список из M2M `idp_group_rows`."""
    return LearningMaterialRead(
        id=row.id,
        title=row.title,
        body=row.body,
        material_type=row.material_type,
        status=row.status,
        idp_groups=[g.idp_group for g in (row.idp_group_rows or [])],
        created_by_sub=row.created_by_sub,
        version=getattr(row, "version", 1) or 1,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get(
    "/learning/materials",
    summary="Список учебных материалов",
    response_model=list[LearningMaterialRead],
)
async def list_materials(
    user: CurrentUser,
    db: DbSession,
    material_type: str | None = Query(default=None),
    status: str | None = Query(default=None, description="Только для администратора"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[LearningMaterialRead]:
    rows = await svc.list_materials(db, user, material_type=material_type, status=status, limit=limit, offset=offset)
    return [_material_to_read(r) for r in rows]


@router.get(
    "/learning/materials/{material_id}",
    summary="Карточка учебного материала",
    response_model=LearningMaterialRead,
)
async def get_material(
    material_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> LearningMaterialRead:
    row = await svc.get_material(db, user, material_id)
    return _material_to_read(row)


@router.post(
    "/learning/materials",
    summary="Создать учебный материал",
    description="Только для администратора портала.",
    response_model=LearningMaterialRead,
    status_code=201,
)
async def create_material(
    user: CurrentUser,
    db: DbSession,
    body: LearningMaterialCreate,
    bg: BackgroundTasks,
) -> LearningMaterialRead:
    row = await svc.create_material(db, user, body)
    read = _material_to_read(row)
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL,
        str(read.id),
        learning_material_to_text(read.title, read.body),
        learning_material_meta(
            created_by_sub=read.created_by_sub,
            status=read.status,
            material_type=read.material_type,
        ),
    )
    return read


@router.delete(
    "/learning/materials/{material_id}",
    summary="Удалить учебный материал",
    description="Только для администратора портала.",
    status_code=204,
)
async def delete_material(
    material_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    bg: BackgroundTasks,
) -> None:
    await svc.delete_material(db, user, material_id)
    bg.add_task(emb_svc.delete_embedding_bg, PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL, str(material_id))


@router.patch(
    "/learning/materials/{material_id}",
    summary="Обновить учебный материал",
    description="Только для администратора портала.",
    response_model=LearningMaterialRead,
)
async def update_material(
    material_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: LearningMaterialUpdate,
    bg: BackgroundTasks,
) -> LearningMaterialRead:
    row = await svc.update_material(db, user, material_id, body)
    read = _material_to_read(row)
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        PORTAL_SEARCH_ENTITY_TYPE_LEARNING_MATERIAL,
        str(read.id),
        learning_material_to_text(read.title, read.body),
        learning_material_meta(
            created_by_sub=read.created_by_sub,
            status=read.status,
            material_type=read.material_type,
        ),
    )
    return read
