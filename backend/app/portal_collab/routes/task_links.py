from __future__ import annotations

import uuid

from fastapi import APIRouter

from app.api.deps import DbSession
from app.api.deps_auth import CurrentUser
from app.portal_collab.schemas.task import TaskLinkCreate, TaskLinkRead
from app.portal_collab.services import task_link as link_svc

router = APIRouter(prefix="/portal", tags=["Задачи"])


@router.get(
    "/tasks/{task_id}/links",
    summary="Список ссылок задачи",
    response_model=list[TaskLinkRead],
)
async def list_task_links(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> list[TaskLinkRead]:
    rows = await link_svc.list_links(db, user, task_id)
    return [TaskLinkRead.model_validate(r) for r in rows]


@router.post(
    "/tasks/{task_id}/links",
    summary="Прикрепить ссылку к задаче",
    response_model=TaskLinkRead,
    status_code=201,
)
async def create_task_link(
    task_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    body: TaskLinkCreate,
) -> TaskLinkRead:
    link = await link_svc.create_link(db, user, task_id, body)
    return TaskLinkRead.model_validate(link)


@router.delete(
    "/tasks/{task_id}/links/{link_id}",
    summary="Удалить ссылку задачи",
    status_code=204,
)
async def delete_task_link(
    task_id: uuid.UUID,
    link_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    await link_svc.delete_link(db, user, task_id, link_id)
