from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_learning.schemas.checklist import (
    ChecklistCreate,
    ChecklistRead,
    ChecklistUpdate,
    MarkItemBody,
    UserChecklistProgressRead,
)
from app.portal_learning.services import checklist as svc

router = APIRouter(tags=["Обучение · Чек-листы"])


@router.get(
    "/learning/checklists",
    summary="Список чек-листов",
    response_model=list[ChecklistRead],
)
async def list_checklists(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[ChecklistRead]:
    rows = await svc.list_checklists(db, user, limit=limit, offset=offset)
    return [ChecklistRead.model_validate(r) for r in rows]


@router.get(
    "/learning/checklists/{checklist_id}",
    summary="Карточка чек-листа",
    response_model=ChecklistRead,
)
async def get_checklist(
    checklist_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> ChecklistRead:
    row = await svc.get_checklist(db, user, checklist_id)
    return ChecklistRead.model_validate(row)


@router.post(
    "/learning/checklists",
    summary="Создать чек-лист",
    description="Только для администратора портала.",
    response_model=ChecklistRead,
    status_code=201,
)
async def create_checklist(
    user: CurrentUser,
    db: DbSession,
    body: ChecklistCreate,
) -> ChecklistRead:
    row = await svc.create_checklist(db, user, body)
    return ChecklistRead.model_validate(row)


@router.patch(
    "/learning/checklists/{checklist_id}",
    summary="Обновить чек-лист",
    description="Только для администратора портала.",
    response_model=ChecklistRead,
)
async def update_checklist(
    checklist_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: ChecklistUpdate,
) -> ChecklistRead:
    row = await svc.update_checklist(db, user, checklist_id, body)
    return ChecklistRead.model_validate(row)


@router.post(
    "/learning/checklists/{checklist_id}/start",
    summary="Начать прохождение чек-листа",
    response_model=UserChecklistProgressRead,
    status_code=201,
)
async def start_checklist(
    checklist_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> UserChecklistProgressRead:
    row = await svc.start_checklist(db, user, checklist_id)
    return UserChecklistProgressRead.model_validate(row)


@router.get(
    "/learning/checklists/{checklist_id}/my-progress",
    summary="Мой прогресс по чек-листу",
    response_model=UserChecklistProgressRead,
)
async def my_progress(
    checklist_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> UserChecklistProgressRead:
    row = await svc.get_my_progress(db, user, checklist_id)
    return UserChecklistProgressRead.model_validate(row)


@router.patch(
    "/learning/checklists/{checklist_id}/items/{item_id}",
    summary="Отметить пункт чек-листа",
    response_model=UserChecklistProgressRead,
)
async def mark_item(
    checklist_id: uuid.UUID,
    item_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: MarkItemBody,
) -> UserChecklistProgressRead:
    row = await svc.mark_item(db, user, checklist_id, item_id, body)
    return UserChecklistProgressRead.model_validate(row)


@router.delete(
    "/learning/checklists/{checklist_id}",
    summary="Удалить чек-лист",
    description="Только для администратора портала. Удаляет прогресс пользователей.",
    status_code=204,
)
async def delete_checklist_row(
    checklist_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await svc.delete_checklist(db, user, checklist_id)
