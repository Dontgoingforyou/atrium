from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_collab.schemas.agreement import PortalAgreementCreate, PortalAgreementRead, PortalAgreementUpdate
from app.portal_collab.services import agreement as svc
from app.portal_search.services import embedding as emb_svc
from app.portal_search.services.entity_text import agreement_meta, agreement_to_text

router = APIRouter(prefix="/portal", tags=["Договорённости"])


@router.get(
    "/agreements",
    summary="Список договорённостей",
    response_model=list[PortalAgreementRead],
)
async def list_agreements(
    user: CurrentUser,
    db: DbSession,
    status: str | None = Query(default=None),
    document_id: uuid.UUID | None = Query(default=None),
    task_id: uuid.UUID | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[PortalAgreementRead]:
    rows = await svc.list_agreements(
        db,
        user,
        status=status,
        document_id=document_id,
        task_id=task_id,
        skip=skip,
        limit=limit,
    )
    return [PortalAgreementRead.model_validate(r) for r in rows]


@router.post(
    "/agreements",
    summary="Создать договорённость",
    response_model=PortalAgreementRead,
    status_code=201,
)
async def create_agreement(
    user: CurrentUser,
    db: DbSession,
    body: PortalAgreementCreate,
    bg: BackgroundTasks,
) -> PortalAgreementRead:
    row = await svc.create_agreement(db, user, body)
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        "agreement",
        str(row.id),
        agreement_to_text(row.body),
        agreement_meta(
            created_by_sub=row.created_by_sub,
            status=row.status,
        ),
    )
    return PortalAgreementRead.model_validate(row)


@router.get(
    "/agreements/{agreement_id}",
    summary="Договорённость по ID",
    response_model=PortalAgreementRead,
)
async def get_agreement(
    agreement_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> PortalAgreementRead:
    row = await svc.get_agreement(db, user, agreement_id)
    return PortalAgreementRead.model_validate(row)


@router.patch(
    "/agreements/{agreement_id}",
    summary="Обновить договорённость",
    response_model=PortalAgreementRead,
)
async def update_agreement(
    agreement_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: PortalAgreementUpdate,
    bg: BackgroundTasks,
) -> PortalAgreementRead:
    row = await svc.update_agreement(db, user, agreement_id, body)
    bg.add_task(
        emb_svc.upsert_embedding_bg,
        "agreement",
        str(row.id),
        agreement_to_text(row.body),
        agreement_meta(
            created_by_sub=row.created_by_sub,
            status=row.status,
        ),
    )
    return PortalAgreementRead.model_validate(row)
